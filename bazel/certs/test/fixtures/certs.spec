# Exercises every section kind supported by //certs:gen. See ../../README.md
# for the spec grammar.

[cert ca]
key = ca_key.pem
cfg = ca.cfg
serial = 1234
out = ca_cert.pem
info_header = ca_cert_info.h
hash_header = ca_cert_hash.h

[cert leaf]
key = leaf_key.pem
cfg = leaf.cfg
section = v3_leaf
issuer = ca
out = none
info_header = leaf_cert_info.h
hash_header = leaf_cert_hash.h

[concat chain.pem]
parts = leaf,ca

[crl revoked.crl.pem]
issuer = ca
revoke = leaf

[p12 bundle.p12]
cert = leaf
chain = ca
password_file = p12_password.txt

[p12 unencrypted.p12]
cert = leaf
chain = ca
encrypt = none

[cert ec_responder]
key = ec_key.pem
cfg = leaf.cfg
section = v3_leaf
issuer = self
out = ec_responder.pem

[ocsp statuses.der]
responder = ca
responder_id = name
cert = ca
issuer = ca
status = good
cert = leaf
issuer = ca
status = revoked
cert = leaf
issuer = ca
status = unknown
next_update_days = 30
info_header = ocsp_info.h

[ocsp ec_status.der]
responder = ec_responder
responder_id = key
cert = ca
issuer = ca
status = good

[trust_bundle trust-bundle.json]
domain = example.org:ca:7
domain = other.example:ca:9

[cert expired]
key = encrypted_key.pem
key_password = passphrase
cfg = leaf.cfg
section = v3_leaf
issuer = ca
validity = expired
out = expired.pem
info_header = expired_cert_info.h

[cert long]
key = leaf_key.pem
cfg = leaf.cfg
section = v3_leaf
issuer = ca
validity = long
out = long.pem
info_header = long_cert_info.h

[cert v1]
key = leaf_key.pem
cfg = v1.cfg
issuer = self
out = v1.pem
