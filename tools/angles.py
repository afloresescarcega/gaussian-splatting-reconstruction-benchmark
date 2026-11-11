import struct, sys, math
p, listing = sys.argv[1], sys.argv[2]
b = open(p,'rb').read(); hl = struct.unpack('<H', b[8:10])[0]; data = b[10+hl:]
n = len(data)//(17*8); v = struct.unpack('<%dd' % (n*17), data[:n*17*8])
names = sorted(l.split()[0].split('/')[-1] for l in open(listing) if '/images_4/DSC' in l)
# LLFF layout: rows of 3x5 [R|t|hwf], c2w; camera center = column 3
cs = [(v[i*17+3], v[i*17+8], v[i*17+13]) for i in range(n)]
cx = sum(c[0] for c in cs)/n; cy = sum(c[1] for c in cs)/n; cz = sum(c[2] for c in cs)/n
# orbit plane: pick the two axes with largest spread
spread = [max(c[k] for c in cs)-min(c[k] for c in cs) for k in range(3)]
a, bb = sorted(range(3), key=lambda k: -spread[k])[:2]
ctr = (cx,cy,cz)
for i,(nm,c) in enumerate(zip(names, cs)):
    ang = math.degrees(math.atan2(c[bb]-ctr[bb], c[a]-ctr[a])) % 360
    print(nm, round(ang,1))
