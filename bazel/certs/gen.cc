// Hermetic test-certificate generator.
//
// Replaces OpenSSL-CLI based fixture scripts that used to shell out to the
// OpenSSL CLI to produce test certificates, CRLs and OCSP responses.
// Everything is produced in-process with BoringSSL from a declarative spec
// file so that fixtures are reproducible, year-stamped and free of external
// tooling.
//
// Usage:
//   gen --spec <spec-file> --in-dir <dir> --out-dir <dir> --year <YYYY>
//
// See bazel/certs/README.md for the spec file format.

#include <sys/stat.h>
#include <time.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "openssl/asn1.h"
#include "openssl/bio.h"
#include "openssl/bn.h"
#include "openssl/bytestring.h"
#include "openssl/conf.h"
#include "openssl/digest.h"
#include "openssl/err.h"
#include "openssl/evp.h"
#include "openssl/mem.h"
#include "openssl/objects.h"
#include "openssl/pem.h"
#include "openssl/pkcs8.h"
#include "openssl/rsa.h"
#include "openssl/sha.h"
#include "openssl/stack.h"
#include "openssl/x509.h"
#include "openssl/x509v3.h"

namespace {

// CRL nextUpdate offset. Matches `default_crl_days` in the CA configs.
constexpr int CrlDays = 3650;
// clang-format's column limit; the generated headers used to be reformatted by
// the repository's format checks, so reproduce the same wrapping here.
constexpr size_t ColumnLimit = 100;

[[noreturn]] void fail(const std::string& message) {
  std::cerr << "testcerts: " << message << std::endl;
  ERR_print_errors_fp(stderr);
  exit(1);
}

void check(bool ok, const std::string& message) {
  if (!ok) {
    fail(message);
  }
}

std::string trim(const std::string& in) {
  size_t begin = in.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return "";
  }
  size_t end = in.find_last_not_of(" \t\r\n");
  return in.substr(begin, end - begin + 1);
}

std::vector<std::string> splitList(const std::string& in) {
  std::vector<std::string> out;
  std::stringstream ss(in);
  std::string item;
  while (std::getline(ss, item, ',')) {
    std::string trimmed = trim(item);
    if (!trimmed.empty()) {
      out.push_back(trimmed);
    }
  }
  return out;
}

std::string readFile(const std::string& path) {
  std::ifstream file(path, std::ios::binary);
  check(file.good(), "unable to read " + path);
  std::ostringstream contents;
  contents << file.rdbuf();
  return contents.str();
}

void writeFile(const std::string& path, const std::string& contents) {
  std::ofstream file(path, std::ios::binary | std::ios::trunc);
  check(file.good(), "unable to write " + path);
  file.write(contents.data(), static_cast<std::streamsize>(contents.size()));
  check(file.good(), "unable to write " + path);
}

std::string toUpper(std::string in) {
  std::transform(in.begin(), in.end(), in.begin(),
                 [](unsigned char c) { return static_cast<char>(toupper(c)); });
  return in;
}

std::string hexEncode(const uint8_t* data, size_t len, bool upper, const char* separator) {
  static const char* kLower = "0123456789abcdef";
  static const char* kUpper = "0123456789ABCDEF";
  const char* alphabet = upper ? kUpper : kLower;
  std::string out;
  for (size_t i = 0; i < len; i++) {
    if (i != 0) {
      out += separator;
    }
    out += alphabet[data[i] >> 4];
    out += alphabet[data[i] & 0xf];
  }
  return out;
}

std::string base64Encode(const uint8_t* data, size_t len, bool url_safe, bool pad) {
  static const char kStd[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  static const char kUrl[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const char* alphabet = url_safe ? kUrl : kStd;
  std::string out;
  size_t i = 0;
  for (; i + 2 < len; i += 3) {
    uint32_t chunk = (uint32_t(data[i]) << 16) | (uint32_t(data[i + 1]) << 8) | data[i + 2];
    out += alphabet[(chunk >> 18) & 0x3f];
    out += alphabet[(chunk >> 12) & 0x3f];
    out += alphabet[(chunk >> 6) & 0x3f];
    out += alphabet[chunk & 0x3f];
  }
  if (i + 1 == len) {
    uint32_t chunk = uint32_t(data[i]) << 16;
    out += alphabet[(chunk >> 18) & 0x3f];
    out += alphabet[(chunk >> 12) & 0x3f];
    if (pad) {
      out += "==";
    }
  } else if (i + 2 == len) {
    uint32_t chunk = (uint32_t(data[i]) << 16) | (uint32_t(data[i + 1]) << 8);
    out += alphabet[(chunk >> 18) & 0x3f];
    out += alphabet[(chunk >> 12) & 0x3f];
    out += alphabet[(chunk >> 6) & 0x3f];
    if (pad) {
      out += "=";
    }
  }
  return out;
}

std::string sha256Hex(const std::string& data) {
  uint8_t digest[SHA256_DIGEST_LENGTH];
  SHA256(reinterpret_cast<const uint8_t*>(data.data()), data.size(), digest);
  return hexEncode(digest, sizeof(digest), false, "");
}

std::string sha1Hex(const std::string& data) {
  uint8_t digest[SHA_DIGEST_LENGTH];
  SHA1(reinterpret_cast<const uint8_t*>(data.data()), data.size(), digest);
  return hexEncode(digest, sizeof(digest), false, "");
}

// ---------------------------------------------------------------------------
// Header emission that mirrors clang-format's wrapping of the previously
// checked-in `*_cert_info.h` / `*cert_hash.h` files.
// ---------------------------------------------------------------------------

// Splits `value` into the atomic pieces clang-format is allowed to break
// between. String literals are only broken after a ':' separator (which is what
// the colon-delimited fingerprints in the hash headers contain); everything else
// is atomic.
std::vector<std::string> literalTokens(const std::string& value) {
  std::vector<std::string> tokens;
  std::string current;
  for (char c : value) {
    current += c;
    if (c == ':') {
      tokens.push_back(current);
      current.clear();
    }
  }
  if (!current.empty()) {
    tokens.push_back(current);
  }
  if (tokens.empty()) {
    tokens.emplace_back("");
  }
  return tokens;
}

// Greedily packs `tokens` into lines that fit within the column limit given the
// supplied indent. Returns false if a single token cannot fit on a line.
bool packLiteral(const std::vector<std::string>& tokens, size_t indent, size_t first_line_prefix,
                 std::vector<std::string>& out_lines) {
  out_lines.clear();
  size_t index = 0;
  bool first = true;
  while (index < tokens.size()) {
    const size_t line_indent = first ? first_line_prefix : indent;
    std::string chunk;
    while (index < tokens.size()) {
      // Reserve room for the surrounding quotes, plus the trailing ';' if this
      // turns out to be the last line.
      const bool would_be_last = (index + 1 == tokens.size());
      const size_t overhead = 2 + (would_be_last ? 1 : 0);
      if (line_indent + chunk.size() + tokens[index].size() + overhead > ColumnLimit) {
        break;
      }
      chunk += tokens[index];
      index++;
    }
    if (chunk.empty()) {
      return false;
    }
    out_lines.push_back(chunk);
    first = false;
  }
  return !out_lines.empty();
}

// Emits `constexpr char <name>[] = "<value>";` formatted the way clang-format
// would have formatted it.
std::string constantDefinition(const std::string& name, const std::string& value) {
  const std::string prefix = "constexpr char " + name + "[] = ";
  if (prefix.size() + value.size() + 3 <= ColumnLimit) {
    return prefix + "\"" + value + "\";\n";
  }

  const std::vector<std::string> tokens = literalTokens(value);

  // Option A: keep the literal on the same line as the assignment, aligning
  // continuations under the opening quote.
  std::vector<std::string> aligned;
  const bool aligned_ok = packLiteral(tokens, prefix.size(), prefix.size(), aligned);

  // Option B: break after '=' and indent continuation lines by four spaces.
  std::vector<std::string> indented;
  const bool indented_ok = packLiteral(tokens, 4, 4, indented);

  const bool use_aligned = aligned_ok && (!indented_ok || aligned.size() <= indented.size());

  std::string out;
  if (use_aligned) {
    for (size_t i = 0; i < aligned.size(); i++) {
      out += (i == 0) ? prefix : std::string(prefix.size(), ' ');
      out += "\"" + aligned[i] + "\"";
      out += (i + 1 == aligned.size()) ? ";\n" : "\n";
    }
    return out;
  }

  check(indented_ok, "unable to format constant " + name);
  out += "constexpr char " + name + "[] =\n";
  for (size_t i = 0; i < indented.size(); i++) {
    out += "    \"" + indented[i] + "\"";
    out += (i + 1 == indented.size()) ? ";\n" : "\n";
  }
  return out;
}

// ---------------------------------------------------------------------------
// Spec file parsing.
// ---------------------------------------------------------------------------

struct Section {
  std::string kind;
  std::string name;
  std::vector<std::pair<std::string, std::string>> values;

  bool has(const std::string& key) const {
    for (const auto& entry : values) {
      if (entry.first == key) {
        return true;
      }
    }
    return false;
  }

  std::string get(const std::string& key, const std::string& fallback = "") const {
    for (const auto& entry : values) {
      if (entry.first == key) {
        return entry.second;
      }
    }
    return fallback;
  }

  std::string require(const std::string& key) const {
    check(has(key), "section [" + kind + " " + name + "] is missing required key '" + key + "'");
    return get(key);
  }

  std::vector<std::string> getAll(const std::string& key) const {
    std::vector<std::string> out;
    for (const auto& entry : values) {
      if (entry.first == key) {
        out.push_back(entry.second);
      }
    }
    return out;
  }
};

std::vector<Section> parseSpec(const std::string& path) {
  std::vector<Section> sections;
  std::ifstream file(path);
  check(file.good(), "unable to read spec " + path);
  std::string line;
  int line_number = 0;
  while (std::getline(file, line)) {
    line_number++;
    const std::string trimmed = trim(line);
    if (trimmed.empty() || trimmed[0] == '#') {
      continue;
    }
    if (trimmed.front() == '[') {
      check(trimmed.back() == ']',
            path + ":" + std::to_string(line_number) + ": unterminated section header");
      const std::string header = trim(trimmed.substr(1, trimmed.size() - 2));
      const size_t space = header.find(' ');
      Section section;
      if (space == std::string::npos) {
        section.kind = header;
      } else {
        section.kind = header.substr(0, space);
        section.name = trim(header.substr(space + 1));
      }
      sections.push_back(std::move(section));
      continue;
    }
    check(!sections.empty(), path + ":" + std::to_string(line_number) + ": value outside section");
    const size_t equals = trimmed.find('=');
    check(equals != std::string::npos,
          path + ":" + std::to_string(line_number) + ": expected 'key = value'");
    sections.back().values.emplace_back(trim(trimmed.substr(0, equals)),
                                        trim(trimmed.substr(equals + 1)));
  }
  return sections;
}

// ---------------------------------------------------------------------------
// The generator itself.
// ---------------------------------------------------------------------------

class Generator {
public:
  Generator(std::string in_dir, std::string out_dir, int year)
      : in_dir_(std::move(in_dir)), out_dir_(std::move(out_dir)), year_(year) {}

  void run(const std::vector<Section>& sections) {
    for (const Section& section : sections) {
      if (section.kind == "cert") {
        makeCert(section);
      } else if (section.kind == "concat") {
        makeConcat(section);
      } else if (section.kind == "crl") {
        makeCrl(section);
      } else if (section.kind == "p12") {
        makeP12(section);
      } else if (section.kind == "ocsp") {
        makeOcsp(section);
      } else if (section.kind == "trust_bundle") {
        makeTrustBundle(section);
      } else {
        fail("unknown spec section kind '" + section.kind + "'");
      }
    }
  }

private:
  struct Fixture {
    bssl::UniquePtr<X509> cert;
    bssl::UniquePtr<EVP_PKEY> key;
    std::string pem;
    std::string out_name;
  };

  std::string inPath(const std::string& name) const { return in_dir_ + "/" + name; }
  std::string outPath(const std::string& name) const { return out_dir_ + "/" + name; }

  const Fixture& fixture(const std::string& name) const {
    auto it = fixtures_.find(name);
    check(it != fixtures_.end(), "unknown fixture '" + name + "'");
    return it->second;
  }

  // -- time helpers ---------------------------------------------------------

  static int64_t utcSeconds(int year, int month, int day) {
    struct tm parts;
    memset(&parts, 0, sizeof(parts));
    parts.tm_year = year - 1900;
    parts.tm_mon = month - 1;
    parts.tm_mday = day;
    const time_t seconds = timegm(&parts);
    check(seconds != static_cast<time_t>(-1), "unable to compute a UTC timestamp");
    return static_cast<int64_t>(seconds);
  }

  // The instant all "current" fixtures start at: Jan 1 of the stamped year.
  int64_t epoch() const { return utcSeconds(year_, 1, 1); }

  static bssl::UniquePtr<ASN1_TIME> asn1Time(int64_t seconds) {
    bssl::UniquePtr<ASN1_TIME> time(ASN1_TIME_set(nullptr, static_cast<time_t>(seconds)));
    check(time != nullptr, "unable to encode an ASN.1 time");
    return time;
  }

  static std::string generalizedTime(int64_t seconds) {
    const time_t as_time = static_cast<time_t>(seconds);
    struct tm parts;
    check(gmtime_r(&as_time, &parts) != nullptr, "unable to break down a timestamp");
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%04d%02d%02d%02d%02d%02dZ", parts.tm_year + 1900,
             parts.tm_mon + 1, parts.tm_mday, parts.tm_hour, parts.tm_min, parts.tm_sec);
    return buffer;
  }

  static std::string printTime(const ASN1_TIME* time) {
    bssl::UniquePtr<BIO> bio(BIO_new(BIO_s_mem()));
    check(ASN1_TIME_print(bio.get(), time) == 1, "unable to print an ASN.1 time");
    const uint8_t* data = nullptr;
    size_t len = 0;
    check(BIO_mem_contents(bio.get(), &data, &len) == 1, "unable to read printed time");
    return std::string(reinterpret_cast<const char*>(data), len);
  }

  void validityRange(const std::string& mode, int64_t* not_before, int64_t* not_after) const {
    if (mode == "current") {
      *not_before = epoch();
      *not_after = utcSeconds(year_ + 2, 1, 1);
    } else if (mode == "expired") {
      *not_before = utcSeconds(2020, 1, 1);
      *not_after = utcSeconds(2021, 1, 1);
    } else if (mode == "long") {
      *not_before = epoch();
      *not_after = utcSeconds(year_ + 50, 1, 1);
    } else {
      fail("unknown validity mode '" + mode + "'");
    }
  }

  // -- key/serial helpers ---------------------------------------------------

  bssl::UniquePtr<EVP_PKEY> loadKey(const std::string& file, const std::string& password) {
    const std::string path = inPath(file);
    bssl::UniquePtr<BIO> bio(BIO_new_file(path.c_str(), "rb"));
    check(bio != nullptr, "unable to open key " + path);
    // PEM_read_bio_PrivateKey treats a non-null, empty callback argument as an
    // empty password, so pass nullptr when no password is configured.
    void* pass = password.empty() ? nullptr : const_cast<char*>(password.c_str());
    bssl::UniquePtr<EVP_PKEY> key(
        PEM_read_bio_PrivateKey(bio.get(), nullptr, nullptr, const_cast<void*>(pass)));
    check(key != nullptr, "unable to parse key " + path);
    return key;
  }

  // Serial numbers must be stable across regenerations because CRL entries and
  // OCSP responses reference them. They are either pinned in the spec or
  // derived from a hash of the fixture name.
  static bssl::UniquePtr<ASN1_INTEGER> serialFor(const std::string& name,
                                                 const std::string& pinned) {
    std::vector<uint8_t> bytes;
    if (!pinned.empty()) {
      std::string hex = pinned;
      if (hex.rfind("0x", 0) == 0 || hex.rfind("0X", 0) == 0) {
        hex = hex.substr(2);
      }
      if (hex.size() % 2 != 0) {
        hex.insert(hex.begin(), '0');
      }
      for (size_t i = 0; i < hex.size(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(strtoul(hex.substr(i, 2).c_str(), nullptr, 16)));
      }
    } else {
      uint8_t digest[SHA256_DIGEST_LENGTH];
      SHA256(reinterpret_cast<const uint8_t*>(name.data()), name.size(), digest);
      bytes.assign(digest, digest + 8);
      // Keep the value positive and non-zero.
      bytes[0] &= 0x7f;
      bytes[0] |= 0x01;
    }
    bssl::UniquePtr<BIGNUM> bn(BN_bin2bn(bytes.data(), bytes.size(), nullptr));
    check(bn != nullptr, "unable to build serial number");
    bssl::UniquePtr<ASN1_INTEGER> serial(BN_to_ASN1_INTEGER(bn.get(), nullptr));
    check(serial != nullptr, "unable to encode serial number");
    return serial;
  }

  static std::string serialHex(const X509* cert) {
    bssl::UniquePtr<BIGNUM> bn(ASN1_INTEGER_to_BN(X509_get0_serialNumber(cert), nullptr));
    check(bn != nullptr, "unable to decode serial number");
    bssl::UniquePtr<char> hex(BN_bn2hex(bn.get()));
    check(hex != nullptr, "unable to print serial number");
    std::string out(hex.get());
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) { return static_cast<char>(tolower(c)); });
    if (out.size() % 2 != 0) {
      out.insert(out.begin(), '0');
    }
    return out;
  }

  // -- subject names --------------------------------------------------------

  // Reproduces `openssl req -batch`: every entry in [req_distinguished_name]
  // that has a matching `<field>_default` becomes a name component, in file
  // order. The NID -> ASN.1 string type mapping below mirrors OpenSSL's
  // `utf8only` string mask / `ASN1_STRING_TABLE` defaults (UTF8String unless a
  // field has a narrower table entry).
  static bssl::UniquePtr<X509_NAME> subjectName(CONF* conf, const std::string& section) {
    bssl::UniquePtr<X509_NAME> name(X509_NAME_new());
    check(name != nullptr, "unable to allocate a name");
    const STACK_OF(CONF_VALUE)* entries = NCONF_get_section(conf, section.c_str());
    if (entries == nullptr) {
      ERR_clear_error();
      return name;
    }
    std::map<std::string, std::string> lookup;
    for (size_t i = 0; i < sk_CONF_VALUE_num(entries); i++) {
      const CONF_VALUE* entry = sk_CONF_VALUE_value(entries, i);
      lookup[entry->name] = entry->value;
    }
    for (size_t i = 0; i < sk_CONF_VALUE_num(entries); i++) {
      const CONF_VALUE* entry = sk_CONF_VALUE_value(entries, i);
      std::string key = entry->name;
      if (key.size() > 8 && key.compare(key.size() - 8, 8, "_default") == 0) {
        continue;
      }
      if (key.size() > 4 && (key.compare(key.size() - 4, 4, "_min") == 0 ||
                             key.compare(key.size() - 4, 4, "_max") == 0)) {
        continue;
      }
      auto value = lookup.find(key + "_default");
      if (value == lookup.end()) {
        continue;
      }
      // OpenSSL allows a numeric prefix (e.g. `0.organizationName`) so that a
      // field can appear more than once.
      std::string field = key;
      const size_t dot = field.find('.');
      if (dot != std::string::npos && field.find_first_not_of("0123456789") >= dot) {
        field = field.substr(dot + 1);
      }
      const int nid = OBJ_txt2nid(field.c_str());
      check(nid != NID_undef, "unknown name field '" + field + "'");
      int type = V_ASN1_UTF8STRING;
      if (nid == NID_countryName || nid == NID_serialNumber || nid == NID_dnQualifier) {
        type = V_ASN1_PRINTABLESTRING;
      } else if (nid == NID_pkcs9_emailAddress || nid == NID_domainComponent) {
        type = V_ASN1_IA5STRING;
      }
      check(X509_NAME_add_entry_by_NID(name.get(), nid, type,
                                       reinterpret_cast<const uint8_t*>(value->second.data()),
                                       static_cast<int>(value->second.size()), -1, 0) == 1,
            "unable to add name entry '" + field + "'");
    }
    return name;
  }

  // -- certificates ---------------------------------------------------------

  void makeCert(const Section& section) {
    const std::string& name = section.name;
    const std::string cfg_file = section.require("cfg");
    const std::string ext_section = section.get("section", "v3_ca");
    const std::string issuer_name = section.get("issuer", "self");
    const std::string validity = section.get("validity", "current");
    const std::string out_name = section.get("out", name + "_cert.pem");

    bssl::UniquePtr<CONF> conf(NCONF_new(nullptr));
    check(conf != nullptr, "unable to allocate a config");
    long error_line = 0;
    check(NCONF_load(conf.get(), inPath(cfg_file).c_str(), &error_line) == 1,
          "unable to load " + inPath(cfg_file) + " (line " + std::to_string(error_line) + ")");

    bssl::UniquePtr<EVP_PKEY> key = loadKey(section.require("key"), section.get("key_password"));

    bssl::UniquePtr<X509> cert(X509_new());
    check(cert != nullptr, "unable to allocate a certificate");

    bssl::UniquePtr<ASN1_INTEGER> serial = serialFor(name, section.get("serial"));
    check(X509_set_serialNumber(cert.get(), serial.get()) == 1, "unable to set serial number");

    int64_t not_before = 0;
    int64_t not_after = 0;
    validityRange(validity, &not_before, &not_after);
    check(X509_set1_notBefore(cert.get(), asn1Time(not_before).get()) == 1,
          "unable to set notBefore");
    check(X509_set1_notAfter(cert.get(), asn1Time(not_after).get()) == 1, "unable to set notAfter");

    bssl::UniquePtr<X509_NAME> subject =
        subjectName(conf.get(), section.get("subject_section", "req_distinguished_name"));
    check(X509_set_subject_name(cert.get(), subject.get()) == 1, "unable to set subject");
    check(X509_set_pubkey(cert.get(), key.get()) == 1, "unable to set public key");

    X509* issuer_cert = cert.get();
    EVP_PKEY* signing_key = key.get();
    if (issuer_name != "self") {
      const Fixture& issuer = fixture(issuer_name);
      issuer_cert = issuer.cert.get();
      signing_key = issuer.key.get();
    }
    check(X509_set_issuer_name(cert.get(), X509_get_subject_name(issuer_cert)) == 1,
          "unable to set issuer");

    // v3 extensions from the `.cfg` file. The context has to be established
    // first so that `subjectKeyIdentifier=hash` and
    // `authorityKeyIdentifier=keyid:always` can be resolved.
    bool has_extensions = false;
    if (NCONF_get_section(conf.get(), ext_section.c_str()) != nullptr) {
      X509V3_CTX ctx;
      X509V3_set_ctx(&ctx, issuer_cert, cert.get(), nullptr, nullptr, 0);
      X509V3_set_nconf(&ctx, conf.get());
      check(X509V3_EXT_add_nconf(conf.get(), &ctx, ext_section.c_str(), cert.get()) == 1,
            "unable to apply extensions from [" + ext_section + "] of " + cfg_file);
      has_extensions = X509_get_ext_count(cert.get()) > 0;
    } else {
      ERR_clear_error();
    }
    // Mirror OpenSSL: a certificate without extensions is emitted as v1.
    check(X509_set_version(cert.get(), has_extensions ? X509_VERSION_3 : X509_VERSION_1) == 1,
          "unable to set version");

    check(X509_sign(cert.get(), signing_key, EVP_sha256()) > 0, "unable to sign " + name);

    bssl::UniquePtr<BIO> bio(BIO_new(BIO_s_mem()));
    check(PEM_write_bio_X509(bio.get(), cert.get()) == 1, "unable to serialize " + name);
    const uint8_t* pem_data = nullptr;
    size_t pem_len = 0;
    check(BIO_mem_contents(bio.get(), &pem_data, &pem_len) == 1, "unable to read PEM");

    Fixture fix;
    fix.pem = std::string(reinterpret_cast<const char*>(pem_data), pem_len);
    fix.out_name = out_name;
    fix.cert = std::move(cert);
    fix.key = std::move(key);

    // `out = none` keeps a fixture available for chaining/CRLs without emitting
    // a file of its own.
    if (out_name != "none") {
      writeFile(outPath(out_name), fix.pem);
    }

    if (section.has("info_header")) {
      writeInfoHeader(section.get("info_header_prefix", name), *fix.cert,
                      section.get("info_header"));
    }
    if (section.has("hash_header")) {
      writeHashHeader(section.get("hash_header_prefix", name), *fix.cert,
                      section.get("hash_header"));
    }

    fixtures_[name] = std::move(fix);
  }

  static std::string certDer(const X509& cert) {
    uint8_t* buffer = nullptr;
    const int len = i2d_X509(const_cast<X509*>(&cert), &buffer);
    check(len > 0, "unable to DER encode a certificate");
    bssl::UniquePtr<uint8_t> owned(buffer);
    return std::string(reinterpret_cast<const char*>(buffer), len);
  }

  static std::string spkiDer(const X509& cert) {
    X509_PUBKEY* pubkey = X509_get_X509_PUBKEY(const_cast<X509*>(&cert));
    uint8_t* buffer = nullptr;
    const int len = i2d_X509_PUBKEY(pubkey, &buffer);
    check(len > 0, "unable to DER encode a public key");
    bssl::UniquePtr<uint8_t> owned(buffer);
    return std::string(reinterpret_cast<const char*>(buffer), len);
  }

  // RFC 6960 KeyHash: SHA-1 of the responder's public key, excluding the tag
  // and length octets of the BIT STRING.
  static std::string keyHash(const X509& cert) {
    X509_PUBKEY* pubkey = X509_get_X509_PUBKEY(const_cast<X509*>(&cert));
    const uint8_t* key_data = nullptr;
    int key_len = 0;
    check(X509_PUBKEY_get0_param(nullptr, &key_data, &key_len, nullptr, pubkey) == 1,
          "unable to extract a public key");
    uint8_t digest[SHA_DIGEST_LENGTH];
    SHA1(key_data, static_cast<size_t>(key_len), digest);
    return std::string(reinterpret_cast<const char*>(digest), sizeof(digest));
  }

  static std::string nameDer(const X509_NAME* name) {
    uint8_t* buffer = nullptr;
    const int len = i2d_X509_NAME(const_cast<X509_NAME*>(name), &buffer);
    check(len > 0, "unable to DER encode a name");
    bssl::UniquePtr<uint8_t> owned(buffer);
    return std::string(reinterpret_cast<const char*>(buffer), len);
  }

  void writeInfoHeader(const std::string& fixture_name, const X509& cert,
                       const std::string& out_name) {
    const std::string prefix = "TEST_" + toUpper(fixture_name);
    const std::string der = certDer(cert);
    const std::string spki = spkiDer(cert);
    uint8_t spki_digest[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const uint8_t*>(spki.data()), spki.size(), spki_digest);

    std::string out = "#pragma once\n\n";
    out += "// This file is auto-generated by //certs:gen.\n";
    out += constantDefinition(prefix + "_CERT_256_HASH", sha256Hex(der));
    out += constantDefinition(prefix + "_CERT_1_HASH", sha1Hex(der));
    out += constantDefinition(prefix + "_CERT_SPKI",
                              base64Encode(spki_digest, sizeof(spki_digest), false, true));
    out += constantDefinition(prefix + "_CERT_SERIAL", serialHex(&cert));
    out += constantDefinition(prefix + "_CERT_NOT_BEFORE", printTime(X509_get0_notBefore(&cert)));
    out += constantDefinition(prefix + "_CERT_NOT_AFTER", printTime(X509_get0_notAfter(&cert)));
    writeFile(outPath(out_name), out);
  }

  void writeHashHeader(const std::string& fixture_name, const X509& cert,
                       const std::string& out_name) {
    const std::string prefix = "TEST_" + toUpper(fixture_name);
    const std::string der = certDer(cert);
    uint8_t digest[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const uint8_t*>(der.data()), der.size(), digest);

    std::string out = "#pragma once\n\n";
    out += constantDefinition(prefix + "_CERT_HASH", hexEncode(digest, sizeof(digest), true, ":"));
    writeFile(outPath(out_name), out);
  }

  // -- concatenations -------------------------------------------------------

  void makeConcat(const Section& section) {
    std::string out;
    for (const std::string& part : splitList(section.require("parts"))) {
      auto it = fixtures_.find(part);
      if (it != fixtures_.end()) {
        out += it->second.pem;
      } else {
        // Allow referencing files produced earlier in the run (CRLs, chains).
        out += readFile(outPath(part));
      }
    }
    writeFile(outPath(section.name), out);
  }

  // -- CRLs -----------------------------------------------------------------

  void makeCrl(const Section& section) {
    const Fixture& issuer = fixture(section.require("issuer"));
    bssl::UniquePtr<X509_CRL> crl(X509_CRL_new());
    check(crl != nullptr, "unable to allocate a CRL");
    check(X509_CRL_set_version(crl.get(), X509_CRL_VERSION_2) == 1, "unable to set CRL version");
    check(X509_CRL_set_issuer_name(crl.get(), X509_get_subject_name(issuer.cert.get())) == 1,
          "unable to set CRL issuer");

    const int64_t last_update = epoch();
    check(X509_CRL_set1_lastUpdate(crl.get(), asn1Time(last_update).get()) == 1,
          "unable to set CRL lastUpdate");
    check(X509_CRL_set1_nextUpdate(
              crl.get(), asn1Time(last_update + static_cast<int64_t>(CrlDays) * 86400).get()) == 1,
          "unable to set CRL nextUpdate");

    // `openssl ca -gencrl` always emits a crlNumber when a `crlnumber` file is
    // configured; the CA configs seeded it with 00.
    bssl::UniquePtr<ASN1_INTEGER> crl_number(ASN1_INTEGER_new());
    check(ASN1_INTEGER_set(crl_number.get(), 0) == 1, "unable to set CRL number");
    check(X509_CRL_add1_ext_i2d(crl.get(), NID_crl_number, crl_number.get(), 0, 0) == 1,
          "unable to add CRL number");

    for (const std::string& revoked_name : splitList(section.get("revoke"))) {
      const Fixture& revoked_cert = fixture(revoked_name);
      bssl::UniquePtr<X509_REVOKED> revoked(X509_REVOKED_new());
      check(revoked != nullptr, "unable to allocate a CRL entry");
      check(X509_REVOKED_set_serialNumber(revoked.get(),
                                          X509_get0_serialNumber(revoked_cert.cert.get())) == 1,
            "unable to set a revoked serial number");
      check(X509_REVOKED_set_revocationDate(revoked.get(), asn1Time(last_update).get()) == 1,
            "unable to set a revocation date");
      check(X509_CRL_add0_revoked(crl.get(), revoked.get()) == 1, "unable to add a CRL entry");
      revoked.release();
    }

    check(X509_CRL_sort(crl.get()) == 1, "unable to sort a CRL");
    check(X509_CRL_sign(crl.get(), issuer.key.get(), EVP_sha256()) > 0, "unable to sign a CRL");

    bssl::UniquePtr<BIO> bio(BIO_new(BIO_s_mem()));
    check(PEM_write_bio_X509_CRL(bio.get(), crl.get()) == 1, "unable to serialize a CRL");
    const uint8_t* data = nullptr;
    size_t len = 0;
    check(BIO_mem_contents(bio.get(), &data, &len) == 1, "unable to read a CRL");
    writeFile(outPath(section.name), std::string(reinterpret_cast<const char*>(data), len));
  }

  // -- PKCS#12 --------------------------------------------------------------

  void makeP12(const Section& section) {
    const Fixture& leaf = fixture(section.require("cert"));
    std::string password;
    if (section.has("password_file")) {
      password = readFile(inPath(section.get("password_file")));
      while (!password.empty() && (password.back() == '\n' || password.back() == '\r')) {
        password.pop_back();
      }
    } else {
      password = section.get("password");
    }

    bssl::UniquePtr<STACK_OF(X509)> chain(sk_X509_new_null());
    check(chain != nullptr, "unable to allocate a certificate chain");
    for (const std::string& extra : splitList(section.get("chain"))) {
      // The stack owns its elements, so hand it a reference of its own.
      X509* extra_cert = fixture(extra).cert.get();
      X509_up_ref(extra_cert);
      check(sk_X509_push(chain.get(), extra_cert) > 0, "unable to extend a certificate chain");
    }

    const bool encrypt = section.get("encrypt", "default") != "none";
    const int nid = encrypt ? 0 : -1;
    const int mac_iterations = encrypt ? 0 : 1;

    bssl::UniquePtr<PKCS12> p12(PKCS12_create(password.c_str(), nullptr, leaf.key.get(),
                                              leaf.cert.get(), chain.get(), nid, nid, 0,
                                              mac_iterations, 0));
    check(p12 != nullptr, "unable to build " + section.name);

    bssl::UniquePtr<BIO> bio(BIO_new(BIO_s_mem()));
    check(i2d_PKCS12_bio(bio.get(), p12.get()) == 1, "unable to serialize " + section.name);
    const uint8_t* data = nullptr;
    size_t len = 0;
    check(BIO_mem_contents(bio.get(), &data, &len) == 1, "unable to read " + section.name);
    writeFile(outPath(section.name), std::string(reinterpret_cast<const char*>(data), len));
  }

  // -- OCSP -----------------------------------------------------------------

  // OIDs, DER encoded.
  static const std::vector<uint8_t>& sha1AlgorithmIdentifier() {
    static const std::vector<uint8_t> value = {0x30, 0x09, 0x06, 0x05, 0x2b, 0x0e,
                                               0x03, 0x02, 0x1a, 0x05, 0x00};
    return value;
  }
  static const std::vector<uint8_t>& sha256RsaAlgorithmIdentifier() {
    static const std::vector<uint8_t> value = {0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86,
                                               0xf7, 0x0d, 0x01, 0x01, 0x0b, 0x05, 0x00};
    return value;
  }
  static const std::vector<uint8_t>& ecdsaSha256AlgorithmIdentifier() {
    static const std::vector<uint8_t> value = {0x30, 0x0a, 0x06, 0x08, 0x2a, 0x86,
                                               0x48, 0xce, 0x3d, 0x04, 0x03, 0x02};
    return value;
  }
  static const std::vector<uint8_t>& signatureAlgorithmIdentifier(const EVP_PKEY* key) {
    switch (EVP_PKEY_id(key)) {
    case EVP_PKEY_RSA:
      return sha256RsaAlgorithmIdentifier();
    case EVP_PKEY_EC:
      return ecdsaSha256AlgorithmIdentifier();
    default:
      fail("unsupported OCSP responder key type");
    }
  }
  // id-pkix-ocsp-basic (1.3.6.1.5.5.7.48.1.1)
  static const std::vector<uint8_t>& ocspBasicOid() {
    static const std::vector<uint8_t> value = {0x2b, 0x06, 0x01, 0x05, 0x05,
                                               0x07, 0x30, 0x01, 0x01};
    return value;
  }

  static void addBytes(CBB* cbb, const std::string& bytes) {
    check(CBB_add_bytes(cbb, reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size()) == 1,
          "unable to append DER bytes");
  }

  static void addOctetString(CBB* cbb, const std::string& bytes) {
    CBB child;
    check(CBB_add_asn1(cbb, &child, CBS_ASN1_OCTETSTRING) == 1, "unable to add an OCTET STRING");
    addBytes(&child, bytes);
    check(CBB_flush(cbb) == 1, "unable to flush an OCTET STRING");
  }

  static void addGeneralizedTime(CBB* cbb, int64_t seconds) {
    CBB child;
    check(CBB_add_asn1(cbb, &child, CBS_ASN1_GENERALIZEDTIME) == 1,
          "unable to add a GeneralizedTime");
    addBytes(&child, generalizedTime(seconds));
    check(CBB_flush(cbb) == 1, "unable to flush a GeneralizedTime");
  }

  // Serializes the full TLV of the certificate's serial number.
  static std::string serialDer(const X509& cert) {
    uint8_t* buffer = nullptr;
    const int len =
        i2d_ASN1_INTEGER(const_cast<ASN1_INTEGER*>(X509_get0_serialNumber(&cert)), &buffer);
    check(len > 0, "unable to DER encode a serial number");
    bssl::UniquePtr<uint8_t> owned(buffer);
    return std::string(reinterpret_cast<const char*>(buffer), len);
  }

  struct SingleResponseSpec {
    const X509* cert;
    const X509* issuer;
    std::string status;
    bool has_next_update;
  };

  void addCertId(CBB* cbb, const SingleResponseSpec& single) {
    CBB cert_id;
    check(CBB_add_asn1(cbb, &cert_id, CBS_ASN1_SEQUENCE) == 1, "unable to add a CertID");
    check(CBB_add_bytes(&cert_id, sha1AlgorithmIdentifier().data(),
                        sha1AlgorithmIdentifier().size()) == 1,
          "unable to add a hash algorithm");
    const std::string issuer_name = nameDer(X509_get_issuer_name(single.cert));
    addOctetString(&cert_id, sha1Raw(issuer_name));
    addOctetString(&cert_id, keyHash(*single.issuer));
    addBytes(&cert_id, serialDer(*single.cert));
    check(CBB_flush(cbb) == 1, "unable to flush a CertID");
  }

  static std::string sha1Raw(const std::string& data) {
    uint8_t digest[SHA_DIGEST_LENGTH];
    SHA1(reinterpret_cast<const uint8_t*>(data.data()), data.size(), digest);
    return std::string(reinterpret_cast<const char*>(digest), sizeof(digest));
  }

  void makeOcsp(const Section& section) {
    const Fixture& responder = fixture(section.require("responder"));
    const std::string responder_id = section.get("responder_id", "name");
    const std::string status = section.get("status", "good");
    const int next_update_days =
        section.has("next_update_days") ? atoi(section.get("next_update_days").c_str()) : -1;

    std::vector<SingleResponseSpec> singles;
    const std::vector<std::string> cert_names = section.getAll("cert");
    const std::vector<std::string> issuer_names = section.getAll("issuer");
    const std::vector<std::string> statuses = section.getAll("status");
    check(!cert_names.empty(), "[ocsp " + section.name + "] requires at least one 'cert'");
    check(issuer_names.size() == cert_names.size(),
          "[ocsp " + section.name + "] requires one 'issuer' per 'cert'");
    for (size_t i = 0; i < cert_names.size(); i++) {
      SingleResponseSpec single;
      single.cert = fixture(cert_names[i]).cert.get();
      single.issuer = fixture(issuer_names[i]).cert.get();
      single.status = (statuses.size() == cert_names.size()) ? statuses[i] : status;
      single.has_next_update = next_update_days >= 0;
      singles.push_back(single);
    }

    const int64_t this_update = epoch();
    const int64_t next_update =
        this_update + static_cast<int64_t>(next_update_days < 0 ? 0 : next_update_days) * 86400;

    // ResponseData
    bssl::ScopedCBB tbs_cbb;
    check(CBB_init(tbs_cbb.get(), 512) == 1, "unable to initialize a CBB");
    {
      CBB response_data;
      check(CBB_add_asn1(tbs_cbb.get(), &response_data, CBS_ASN1_SEQUENCE) == 1,
            "unable to add ResponseData");
      // responderID
      CBB responder_id_cbb;
      if (responder_id == "key") {
        check(CBB_add_asn1(&response_data, &responder_id_cbb,
                           CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 2) == 1,
              "unable to add a byKey responder id");
        addOctetString(&responder_id_cbb, keyHash(*responder.cert));
      } else {
        check(CBB_add_asn1(&response_data, &responder_id_cbb,
                           CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 1) == 1,
              "unable to add a byName responder id");
        addBytes(&responder_id_cbb, nameDer(X509_get_subject_name(responder.cert.get())));
      }
      check(CBB_flush(&response_data) == 1, "unable to flush a responder id");
      // producedAt
      addGeneralizedTime(&response_data, this_update);
      // responses
      CBB responses;
      check(CBB_add_asn1(&response_data, &responses, CBS_ASN1_SEQUENCE) == 1,
            "unable to add responses");
      for (const SingleResponseSpec& single : singles) {
        CBB single_response;
        check(CBB_add_asn1(&responses, &single_response, CBS_ASN1_SEQUENCE) == 1,
              "unable to add a SingleResponse");
        addCertId(&single_response, single);
        if (single.status == "good") {
          CBB good;
          check(CBB_add_asn1(&single_response, &good, CBS_ASN1_CONTEXT_SPECIFIC | 0) == 1,
                "unable to add a good status");
        } else if (single.status == "revoked") {
          CBB revoked;
          check(CBB_add_asn1(&single_response, &revoked,
                             CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 1) == 1,
                "unable to add a revoked status");
          addGeneralizedTime(&revoked, this_update);
        } else if (single.status == "unknown") {
          CBB unknown;
          check(CBB_add_asn1(&single_response, &unknown, CBS_ASN1_CONTEXT_SPECIFIC | 2) == 1,
                "unable to add an unknown status");
        } else {
          fail("unknown OCSP certificate status '" + single.status + "'");
        }
        check(CBB_flush(&single_response) == 1, "unable to flush a certificate status");
        addGeneralizedTime(&single_response, this_update);
        if (single.has_next_update) {
          CBB next;
          check(CBB_add_asn1(&single_response, &next,
                             CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 0) == 1,
                "unable to add a nextUpdate");
          addGeneralizedTime(&next, next_update);
        }
        check(CBB_flush(&responses) == 1, "unable to flush a SingleResponse");
      }
      check(CBB_flush(tbs_cbb.get()) == 1, "unable to flush ResponseData");
    }
    uint8_t* tbs_data = nullptr;
    size_t tbs_len = 0;
    check(CBB_finish(tbs_cbb.get(), &tbs_data, &tbs_len) == 1, "unable to finish ResponseData");
    bssl::UniquePtr<uint8_t> tbs_owned(tbs_data);

    // Signature over ResponseData.
    bssl::UniquePtr<EVP_MD_CTX> md_ctx(EVP_MD_CTX_new());
    check(EVP_DigestSignInit(md_ctx.get(), nullptr, EVP_sha256(), nullptr, responder.key.get()) ==
              1,
          "unable to initialize an OCSP signature");
    size_t signature_len = 0;
    check(EVP_DigestSign(md_ctx.get(), nullptr, &signature_len, tbs_data, tbs_len) == 1,
          "unable to size an OCSP signature");
    std::vector<uint8_t> signature(signature_len);
    check(EVP_DigestSign(md_ctx.get(), signature.data(), &signature_len, tbs_data, tbs_len) == 1,
          "unable to compute an OCSP signature");
    signature.resize(signature_len);

    // BasicOCSPResponse
    bssl::ScopedCBB basic_cbb;
    check(CBB_init(basic_cbb.get(), 1024) == 1, "unable to initialize a CBB");
    {
      CBB basic;
      check(CBB_add_asn1(basic_cbb.get(), &basic, CBS_ASN1_SEQUENCE) == 1,
            "unable to add BasicOCSPResponse");
      check(CBB_add_bytes(&basic, tbs_data, tbs_len) == 1, "unable to add ResponseData");
      const std::vector<uint8_t>& signature_algorithm =
          signatureAlgorithmIdentifier(responder.key.get());
      check(CBB_add_bytes(&basic, signature_algorithm.data(), signature_algorithm.size()) == 1,
            "unable to add a signature algorithm");
      CBB signature_cbb;
      check(CBB_add_asn1(&basic, &signature_cbb, CBS_ASN1_BITSTRING) == 1,
            "unable to add a signature");
      check(CBB_add_u8(&signature_cbb, 0) == 1, "unable to add signature padding");
      check(CBB_add_bytes(&signature_cbb, signature.data(), signature.size()) == 1,
            "unable to add signature bytes");
      // certs [0] EXPLICIT SEQUENCE OF Certificate - always include the
      // responder certificate, matching `openssl ocsp -rsigner`.
      CBB certs_explicit;
      check(CBB_add_asn1(&basic, &certs_explicit,
                         CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 0) == 1,
            "unable to add certs");
      CBB certs;
      check(CBB_add_asn1(&certs_explicit, &certs, CBS_ASN1_SEQUENCE) == 1,
            "unable to add a certificate list");
      addBytes(&certs, certDer(*responder.cert));
      check(CBB_flush(basic_cbb.get()) == 1, "unable to flush BasicOCSPResponse");
    }
    uint8_t* basic_data = nullptr;
    size_t basic_len = 0;
    check(CBB_finish(basic_cbb.get(), &basic_data, &basic_len) == 1,
          "unable to finish BasicOCSPResponse");
    bssl::UniquePtr<uint8_t> basic_owned(basic_data);

    // OCSPResponse
    bssl::ScopedCBB response_cbb;
    check(CBB_init(response_cbb.get(), 1024) == 1, "unable to initialize a CBB");
    {
      CBB response;
      check(CBB_add_asn1(response_cbb.get(), &response, CBS_ASN1_SEQUENCE) == 1,
            "unable to add OCSPResponse");
      CBB status_cbb;
      check(CBB_add_asn1(&response, &status_cbb, CBS_ASN1_ENUMERATED) == 1,
            "unable to add a response status");
      check(CBB_add_u8(&status_cbb, 0) == 1, "unable to add a response status value");
      CBB bytes_explicit;
      check(CBB_add_asn1(&response, &bytes_explicit,
                         CBS_ASN1_CONTEXT_SPECIFIC | CBS_ASN1_CONSTRUCTED | 0) == 1,
            "unable to add responseBytes");
      CBB response_bytes;
      check(CBB_add_asn1(&bytes_explicit, &response_bytes, CBS_ASN1_SEQUENCE) == 1,
            "unable to add ResponseBytes");
      CBB oid;
      check(CBB_add_asn1(&response_bytes, &oid, CBS_ASN1_OBJECT) == 1,
            "unable to add a response type");
      check(CBB_add_bytes(&oid, ocspBasicOid().data(), ocspBasicOid().size()) == 1,
            "unable to add a response type value");
      CBB octets;
      check(CBB_add_asn1(&response_bytes, &octets, CBS_ASN1_OCTETSTRING) == 1,
            "unable to add a response body");
      check(CBB_add_bytes(&octets, basic_data, basic_len) == 1, "unable to add a response body");
      check(CBB_flush(response_cbb.get()) == 1, "unable to flush OCSPResponse");
    }
    uint8_t* response_data = nullptr;
    size_t response_len = 0;
    check(CBB_finish(response_cbb.get(), &response_data, &response_len) == 1,
          "unable to finish OCSPResponse");
    bssl::UniquePtr<uint8_t> response_owned(response_data);

    writeFile(outPath(section.name),
              std::string(reinterpret_cast<const char*>(response_data), response_len));

    if (section.has("info_header")) {
      const std::string prefix = "TEST_" + toUpper(section.get("info_header_prefix", "ocsp"));
      std::string out = "#pragma once\n\n";
      out += "// This file is auto-generated by //certs:gen.\n";
      out += constantDefinition(prefix + "_THIS_UPDATE", printTime(asn1Time(this_update).get()));
      if (next_update_days >= 0) {
        out += constantDefinition(prefix + "_NEXT_UPDATE", printTime(asn1Time(next_update).get()));
      }
      writeFile(outPath(section.get("info_header")), out);
    }
  }

  // -- SPIFFE trust bundle --------------------------------------------------

  void makeTrustBundle(const Section& section) {
    const std::vector<std::string> domains = section.getAll("domain");
    check(!domains.empty(), "[trust_bundle " + section.name + "] requires at least one 'domain'");

    std::string out = "{\n  \"trust_domains\": {\n";
    bool first_domain = true;
    for (const std::string& domain : domains) {
      // <trust domain>:<comma-free cert list separated by '+'>:<sequence number>
      const size_t first_colon = domain.find(':');
      const size_t last_colon = domain.rfind(':');
      check(first_colon != std::string::npos && first_colon != last_colon,
            "malformed trust domain entry '" + domain + "'");
      const std::string trust_domain = domain.substr(0, first_colon);
      const std::string cert_list = domain.substr(first_colon + 1, last_colon - first_colon - 1);
      const std::string sequence_number = domain.substr(last_colon + 1);

      if (!first_domain) {
        out += "    },\n";
      }
      first_domain = false;
      out += "    \"" + trust_domain + "\": {\n";
      out += "      \"sequence_number\": " + sequence_number + ",\n";
      out += "      \"keys\": [\n";

      bool first_key = true;
      std::stringstream certs(cert_list);
      std::string cert_name;
      while (std::getline(certs, cert_name, '+')) {
        cert_name = trim(cert_name);
        if (cert_name.empty()) {
          continue;
        }
        const Fixture& ca = fixture(cert_name);
        const std::string der = certDer(*ca.cert);

        EVP_PKEY* pkey = X509_get0_pubkey(ca.cert.get());
        check(pkey != nullptr, "unable to read a trust bundle public key");
        const RSA* rsa = EVP_PKEY_get0_RSA(pkey);
        check(rsa != nullptr, "trust bundle certificates must use RSA keys");
        const BIGNUM* modulus = RSA_get0_n(rsa);
        std::vector<uint8_t> modulus_bytes(BN_num_bytes(modulus));
        BN_bn2bin(modulus, modulus_bytes.data());

        if (!first_key) {
          out += ",\n";
        }
        first_key = false;
        out += "            {\n";
        out += "              \"kty\": \"RSA\",\n";
        out += "              \"use\": \"x509-svid\",\n";
        out += "              \"x5c\": [\n";
        out += "                \"" +
               base64Encode(reinterpret_cast<const uint8_t*>(der.data()), der.size(), false, true) +
               "\"\n";
        out += "              ],\n";
        out += "              \"n\": \"" +
               base64Encode(modulus_bytes.data(), modulus_bytes.size(), true, false) + "\",\n";
        out += "              \"e\": \"AQAB\"\n";
        out += "            }\n";
      }
      out += "      ]\n";
    }
    out += "    }\n  }\n}\n";
    writeFile(outPath(section.name), out);
  }

  std::string in_dir_;
  std::string out_dir_;
  int year_;
  std::map<std::string, Fixture> fixtures_;
};

} // namespace

int main(int argc, char** argv) {
  std::string spec;
  std::string in_dir = ".";
  std::string out_dir = ".";
  int year = 0;

  for (int i = 1; i < argc; i++) {
    const std::string arg = argv[i];
    auto next = [&]() -> std::string {
      check(i + 1 < argc, "missing value for " + arg);
      return argv[++i];
    };
    if (arg == "--spec") {
      spec = next();
    } else if (arg == "--in-dir") {
      in_dir = next();
    } else if (arg == "--out-dir") {
      out_dir = next();
    } else if (arg == "--year") {
      const std::string value = next();
      char* end = nullptr;
      const long parsed = strtol(value.c_str(), &end, 10);
      check(end != nullptr && *end == '\0' && !value.empty(),
            "--year must be a four digit year, got '" + value + "'");
      year = static_cast<int>(parsed);
    } else {
      fail("unknown argument '" + arg + "'");
    }
  }

  check(!spec.empty(), "--spec is required");
  check(year >= 1970, "--year must be a four digit year, got '" + std::to_string(year) + "'");

  Generator generator(in_dir, out_dir, year);
  generator.run(parseSpec(spec));
  return 0;
}
