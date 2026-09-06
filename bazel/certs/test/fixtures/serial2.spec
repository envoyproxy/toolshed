# Same fixture names as serial.spec, writing to differently named outputs, so
# the test can `cmp` the two and confirm serial derivation is deterministic.

[cert serial_ca]
key = ca_key.pem
cfg = ca.cfg
out = serial_ca_2.pem

[cert serial_leaf]
key = leaf_key.pem
cfg = leaf.cfg
section = v3_leaf
issuer = serial_ca
out = serial_leaf_2.pem
