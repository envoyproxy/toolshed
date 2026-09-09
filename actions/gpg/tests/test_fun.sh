#!/usr/bin/env bash

generate_test_key() {
    local name="${1:-Test User}"
    local email="${2:-test@example.com}"
    local passphrase="${3:-testpassword123}"

    gpgconf --kill gpg-agent || true
    cat > /tmp/test-key-params <<EOF
%echo Generating test GPG key
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: ${name}
Name-Email: ${email}
Passphrase: ${passphrase}
Expire-Date: 0
%commit
%echo Done
EOF

    gpg --batch --gen-key /tmp/test-key-params
}

generate_test_key_no_passphrase() {
    local name="${1:-Test User}"
    local email="${2:-test@example.com}"

    gpgconf --kill gpg-agent || true
    cat > /tmp/test-key-params-nopass <<EOF
%echo Generating test GPG key
%no-protection
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: ${name}
Name-Email: ${email}
Expire-Date: 0
%commit
%echo Done
EOF

    gpg --batch --gen-key /tmp/test-key-params-nopass
}

export_secret_key() {
    local email="${1:-test@example.com}"
    local passphrase="${2:-testpassword123}"

    gpg --batch --yes --pinentry-mode loopback \
        --passphrase "${passphrase}" \
        --armor --export-secret-keys "${email}"
}

clear_keyring() {
    local email="${1:-test@example.com}"
    local fpr

    fpr=$(gpg --list-secret-keys --with-colons "${email}" | \
        awk -F: '/^fpr:/ { print $10; exit }')
    if [[ -n "$fpr" ]]; then
        gpg --batch --yes --delete-secret-and-public-key "$fpr" || true
    fi
}

test_fingerprint_output() {
    local fingerprint="${1}"

    if [[ -z "$fingerprint" ]]; then
        echo "fail:Fingerprint output is empty" >> "$TEST_OUTPUT"
        return 1
    elif [[ ! "$fingerprint" =~ ^[A-F0-9]{40}$ ]]; then
        echo "fail:Fingerprint format is invalid: $fingerprint" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:Fingerprint output is valid: $fingerprint" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_passphrase_output() {
    local passphrase="${1}"
    local expected="${2}"

    if [[ -z "$passphrase" ]]; then
        echo "fail:Passphrase output is empty" >> "$TEST_OUTPUT"
    elif [[ -n "$expected" && "$passphrase" != "$expected" ]]; then
        echo "fail:Passphrase output is incorrect: $passphrase" >> "$TEST_OUTPUT"
    else
        echo "success:Passphrase output is correct" >> "$TEST_OUTPUT"
    fi
}

test_key_in_keyring() {
    local fingerprint="${1}"

    if gpg --list-secret-keys | grep -q "$fingerprint"; then
        echo "success:GPG key is in keyring" >> "$TEST_OUTPUT"
    else
        echo "fail:GPG key not found in keyring" >> "$TEST_OUTPUT"
    fi
}

test_passphrase_file_exists() {
    local path="${1}"

    if [[ -f "$path" ]]; then
        echo "success:Passphrase file exists at $path" >> "$TEST_OUTPUT"
    else
        echo "fail:Passphrase file not found at $path" >> "$TEST_OUTPUT"
    fi
}

test_gpg_config_has_passphrase_file() {
    local expected_path="${1}"
    local gnupghome="${GNUPGHOME:-${HOME}/.gnupg}"

    if grep -q "passphrase-file ${expected_path}" "${gnupghome}/gpg.conf"; then
        echo "success:GPG config contains passphrase-file directive" >> "$TEST_OUTPUT"
    else
        echo "fail:GPG config missing passphrase-file directive" >> "$TEST_OUTPUT"
    fi
}

test_signed_file_exists() {
    local path="${1}"

    if [[ -f "$path" ]]; then
        echo "success:Signed file exists at $path" >> "$TEST_OUTPUT"
    else
        echo "fail:Signed file not found at $path" >> "$TEST_OUTPUT"
    fi
}

test_checksums_file_does_not_exist() {
    local path="${1}"

    if [[ -f "$path" ]]; then
        echo "fail:Checksums file found at $path" >> "$TEST_OUTPUT"
    else
        echo "success:Checksums file does not exist at $path" >> "$TEST_OUTPUT"
    fi
}

test_signature_valid() {
    local signed_file="${1}"
    local fingerprint="${2}"
    local key_fingerprints
    local signing_key
    local verify_output

    if [[ ! -f "$signed_file" ]]; then
        echo "fail:Cannot verify signature - file not found: $signed_file" >> "$TEST_OUTPUT"
        return
    fi
    verify_output=$(gpg --verify "$signed_file" 2>&1)
    if echo "$verify_output" | grep -q "Good signature"; then
        echo "success:Signature is valid" >> "$TEST_OUTPUT"
    else
        echo "fail:Signature verification failed" >> "$TEST_OUTPUT"
        return
    fi
    if [[ -z "$fingerprint" ]]; then
        return
    fi
    signing_key=$(\
        echo "$verify_output" \
            | grep -E "using [A-Z]+ key" \
            | sed -E 's/.*using [A-Z]+ key //' \
            | awk '{print $1}')
    if [[ -z "$signing_key" ]]; then
        echo "fail:Could not extract signing key from verify output" >> "$TEST_OUTPUT"
        return
    fi
    key_fingerprints=$(\
        gpg --list-keys --with-colons --with-subkey-fingerprint "$fingerprint" \
            2>/dev/null \
            | awk -F: '/^fpr:/ { print $10 }' \
            | tr '\n' ' ')
    if [[ -z "$key_fingerprints" ]]; then
        echo "fail:Could not list fingerprints for key $fingerprint" >> "$TEST_OUTPUT"
        return
    fi
    if echo "$key_fingerprints" | grep -qi "$signing_key"; then
        echo "success:Signature is from expected key" >> "$TEST_OUTPUT"
    else
        echo "fail:Signature is not from expected key $fingerprint" >> "$TEST_OUTPUT"
        echo "fail:Signing key was: $signing_key" >> "$TEST_OUTPUT"
    fi

}

test_checksums_contain_files() {
    local checksums_file="${1}"
    shift
    local files=("$@")

    if [[ ! -f "$checksums_file" ]]; then
        echo "fail:Checksums file not found: $checksums_file" >> "$TEST_OUTPUT"
        return 0
    fi

    for file in "${files[@]}"; do
        if grep -q "$file" "$checksums_file"; then
            echo "success:Checksums file contains $file" >> "$TEST_OUTPUT"
        else
            echo "fail:Checksums file missing $file" >> "$TEST_OUTPUT"
        fi
    done
}


test_file_exists() {
    local path="${1}"

    if [[ -f "$path" ]]; then
        echo "success:File exists at $path" >> "$TEST_OUTPUT"
    else
        echo "fail:File not found at $path" >> "$TEST_OUTPUT"
    fi
}

test_file_mode() {
    local path="${1}"
    local expected_mode="${2}"
    local mode

    if [[ ! -e "$path" ]]; then
        echo "fail:Path not found for mode check: $path" >> "$TEST_OUTPUT"
        return
    fi

    mode=$(stat -c '%a' "$path")
    if [[ "$mode" == "$expected_mode" ]]; then
        echo "success:Mode for $path is $expected_mode" >> "$TEST_OUTPUT"
    else
        echo "fail:Mode for $path is $mode (expected $expected_mode)" >> "$TEST_OUTPUT"
    fi
}

# Byte-exact comparison of a file against an expected string (no newline is
# appended to `expected` - include one explicitly if the file should end with
# one). On mismatch a short diff is printed to stderr to aid diagnosis - only
# use this with test material, never with real secrets.
test_file_content_equals() {
    local path="${1}"
    local expected="${2}"
    local expected_file

    if [[ ! -f "$path" ]]; then
        echo "fail:File not found for content check: $path" >> "$TEST_OUTPUT"
        return
    fi

    expected_file=$(mktemp)
    printf '%s' "$expected" > "$expected_file"
    if cmp -s "$path" "$expected_file"; then
        echo "success:File content matches for $path" >> "$TEST_OUTPUT"
    else
        echo "fail:File content mismatch for $path (expected $(stat -c '%s' "$expected_file") bytes, got $(stat -c '%s' "$path") bytes)" >> "$TEST_OUTPUT"
        echo "--- content mismatch for $path (expected vs actual) ---" >&2
        diff "$expected_file" "$path" | head -n 10 >&2 || true
    fi
    rm -f "$expected_file"
}

test_sha256_matches() {
    local path="${1}"
    local expected_sha="${2}"
    local sha

    if [[ ! -f "$path" ]]; then
        echo "fail:File not found for sha256 check: $path" >> "$TEST_OUTPUT"
        return
    fi

    sha=$(sha256sum "$path" | awk '{print $1}')
    if [[ "$sha" == "$expected_sha" ]]; then
        echo "success:SHA256 matches for $path" >> "$TEST_OUTPUT"
    else
        echo "fail:SHA256 mismatch for $path" >> "$TEST_OUTPUT"
    fi
}

test_value_equals() {
    local actual="${1}"
    local expected="${2}"
    local label="${3}"

    if [[ "$actual" == "$expected" ]]; then
        echo "success:${label} matched expected value" >> "$TEST_OUTPUT"
    else
        echo "fail:${label} mismatch: $actual" >> "$TEST_OUTPUT"
    fi
}
