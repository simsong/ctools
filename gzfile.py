#!/usr/bin/env python3
#
"""gzfile.py

Class to let files be opened for reading and writing with automatic compression
"""

import tempfile
import subprocess
import os

class GZFile:
    def __init__(self, name, mode='r', level=6, buffering=-1, encoding=None, errors=None,
                 newline=None, closefd=True, opener=None, auto=False):
        if auto==True and name.endswith(".gz")==False:
            self.passthrough = True
            self.f = open(self.name, mode=mode, buffering=buffering, encoding=encoding, errors=errors,
                          newline=newline, closefd=closefd, opener=opener)
            return
        self.passthrough = False
        self.mode        = mode
        if ('r' in mode) and ('w' in mode):
            raise ValueError('cannot open gz files for both reading and writing')
        if 'r' in mode:
            if not os.path.exists(name):
                raise FileNotFoundError(name)
            encoding     = None if 'b' in mode else 'utf-8'
            self.p       = subprocess.Popen(['gzip', '-c', '-q', '-d'], stdin=open(name, 'rb'), stdout=subprocess.PIPE, encoding=encoding)
            self._fileno = self.p.stdout.fileno()
            self.name    = f'/dev/fd/{self._fileno}'
            self.f       = open(self.name, mode)
        if 'w' in mode:
            self.p = subprocess.Popen(['gzip', f'-{level}'], stdin=subprocess.PIPE, stdout=open(name, 'wb'))
            self.name = name

    def fileno(self):
        return self._fileno

    def read(self, count=-1):
        return self.f.read(count)

    def readline(self, count=-1):
        return self.f.readline(count)

    def write(self, text):
        if self.passthrough:
            return self.f.write(text)
        if isinstance(text, bytes):
            return self.p.stdin.write(text)
        else:
            return self.p.stdin.write(text.encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, err, msg, stack):
        if err:
            raise err
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        if self.passthrough:
            return self.f.__next__()
        if 'r' in self.mode:
            return self.p.stdout.__next__()
        raise RuntimeError("not sure how to __next__ on 'w'")

    def close(self):
        if self.passthrough:
            return self.f.close()
        if 'r' in self.mode:
            self.p.stdout.close()
            del self.p
        if 'w' in self.mode:
            self.p.stdin.close()
            self.p.wait()
            del self.p


if __name__=="__main__":
    with GZFile("test.gz", "w") as f:
        f.write("this is a test\n")

    with GZFile("test.gz", "r") as f:
        data = f.read()
        print("data=", data)
