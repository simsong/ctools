#!/usr/bin/env python3
#
"""gzfile.py

Class to let files be opened for reading and writing with automatic compression
"""

import tempfile
import subprocess

class GZFile:
    def __init__(self, name, mode='r', level=6, buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        self.mode   = mode
        if ('r' in mode) and ('w' in mode):
            raise ValueError('cannot open gz files for both reading and writing')
        if 'r' in mode:
            self.p = subprocess.Popen(['gzcat',name],stdout=subprocess.PIPE)
            self._fileno = self.p.stdout.fileno()
            self.name   = f'/dev/fd/{self._fileno}'
            self.f      = open(self.name,mode)
        if 'w' in mode:
            self.p = subprocess.Popen(['gzip',f'-{level}'],stdin=subprocess.PIPE,stdout=open(name,'wb'))
    def fileno(self):
        return self._fileno
    
    def read(self,size=-1):
        return self.f.read(size)

    def write(self,text):
        if isinstance(text,bytes):
            return self.p.stdin.write(text)
        else:
            return self.p.stdin.write(text.encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self,err,msg,stack):
        if err:
            raise err
        if 'r' in self.mode:
            self.p.stdout.close()
            del self.p
        if 'w' in self.mode:
            self.p.stdin.close()
            self.p.wait()
            del self.p

if __name__=="__main__":
    with GZFile("test.gz","w") as f:
        f.write("this is a test\n")

    with GZFile("test.gz","r") as f:
        data = f.read()
        print("data=",data)

    
