[cert ca]
key = ca_key.pem
cfg = ca.cfg

[ocsp status.der]
responder = ca
cert = ca
issuer = ca
status = questionable
