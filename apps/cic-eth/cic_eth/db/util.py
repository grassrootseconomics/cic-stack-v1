import math

def num_serialize(n):
    if n == 0:
        return b'\x00'
    binlog = math.log2(n)
    bytelength = int(binlog / 8 + 1)
    return n.to_bytes(bytelength, 'big')
