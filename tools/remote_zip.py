"""Extract selected members from a remote zip via HTTP Range requests.
usage: python3 -I remote_zip.py URL OUTDIR list <prefix>
       python3 -I remote_zip.py URL OUTDIR get <member> [<member> ...]
"""
import io, os, sys, zipfile, urllib.request

class HttpFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method='HEAD')
        self.size = int(urllib.request.urlopen(req).headers['Content-Length'])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b''
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        data = urllib.request.urlopen(req).read()
        self.pos += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

url, out, cmd, *args = sys.argv[1:]
zf = zipfile.ZipFile(io.BufferedReader(HttpFile(url), buffer_size=1 << 20))
if cmd == 'list':
    for i in zf.infolist():
        if i.filename.startswith(args[0]): print(i.filename, i.file_size)
else:
    for m in args:
        dest = os.path.join(out, m)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zf.open(m) as src, open(dest, 'wb') as dst: dst.write(src.read())
        print('got', m)
