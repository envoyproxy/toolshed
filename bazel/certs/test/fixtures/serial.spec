# Two independent instantiations of the same fixture names, used to assert
# that serial numbers (and therefore the resulting certificates) are
# deterministic: same fixture name -> same derived serial -> identical bytes.

[cert serial_ca]
key = ca_key.pem
cfg = ca.cfg
out = serial_ca.pem

[cert serial_leaf]
key = leaf_key.pem
cfg = leaf.cfg
section = v3_leaf
issuer = serial_ca
out = serial_leaf.pem
