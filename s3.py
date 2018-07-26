from urllib.parse import urlparse
from subprocess import run,Popen,PIPE
import copy
import json
import os
import tempfile

# Tools for reading and write files from Amazon S3 without boto or boto3
# http://boto.cloudhackers.com/en/latest/s3_tut.html
# but it is easier to use the aws cli, since it's configured to work.

def s3open(path, mode="r", encoding=None):
    """
    Open an s3 file for reading or writing. Can handle any size, but cannot seek.
    We could use boto.
    http://boto.cloudhackers.com/en/latest/s3_tut.html
    but it is easier to use the aws cli, since it is present and more likely to work.
    """
    from subprocess import run,PIPE,Popen
    if "b" in mode:
        assert encoding == None
    else:
        if encoding==None:
            encoding="utf-8"
    assert 'a' not in mode
    assert '+' not in mode
    
    if "r" in mode:
        p = Popen(['aws','s3','cp',path,'-'],stdout=PIPE,encoding=encoding)
        return p.stdout

    elif "w" in mode:
        p = Popen(['aws','s3','cp','-',path],stdin=PIPE,encoding=encoding)
        return p.stdin
    else:
        raise RuntimeError("invalid mode:{}".format(mode))


def s3exists(path):
    """Return True if the S3 file exists"""
    out = Popen(['aws','s3','ls','--page-size','10',path],stdout=PIPE,encoding='utf-8').communicate()[0]
    return len(out) > 0




CACHE_SIZE=4096                 # big enough for front and back caches
MAX_READ=65536*16
debug=False
class S3File:
    """Open an S3 file that can be seeked. This is done by caching to the local file system."""
    def __init__(self,name,mode='rb'):
        self.name   = name
        self.url    = urlparse(name)
        if self.url.scheme != 's3':
            raise RuntimeError("url scheme is {}; expecting s3".format(url.scheme))
        self.bucket = self.url.netloc
        self.key    = self.url.path[1:]
        self.fpos   = 0
        self.tf     = tempfile.NamedTemporaryFile()
        cmd = ['aws','s3api','list-objects','--bucket',self.bucket,'--prefix',self.key,'--output','json']
        data = json.loads(Popen(cmd,encoding='utf8',stdout=PIPE).communicate()[0])
        file_info = data['Contents'][0]
        self.length = file_info['Size']
        self.ETag   = file_info['ETag']

        # Load the caches

        self.frontcache = self._readrange(0,CACHE_SIZE) # read the first 1024 bytes and get length of the file
        if self.length > CACHE_SIZE:
            self.backcache_start = self.length-CACHE_SIZE
            if debug: print("backcache starts at {}".format(self.backcache_start))
            self.backcache  = self._readrange(self.backcache_start,CACHE_SIZE)
        else:
            self.backcache  = None

    def _readrange(self,start,length):
        # This is gross; we copy everything to the named temporary file, rather than a pipe
        # because the pipes weren't showing up in /dev/fd/?
        # We probably want to cache also... That's coming
        cmd = ['aws','s3api','get-object','--bucket',self.bucket,'--key',self.key,'--output','json',
               '--range','bytes={}-{}'.format(start,start+length-1),self.tf.name]
        if debug:print(cmd)
        data = json.loads(Popen(cmd,encoding='utf8',stdout=PIPE).communicate()[0])
        if debug:print(data)
        self.tf.seek(0)         # go to the beginning of the data just read
        return self.tf.read(length) # and read that much
        
    def __repr__(self):
        return "FakeFile<name:{} url:{}>".format(self.name,self.url)

    def read(self,length=-1):
        # If length==-1, figure out the max we can read to the end of the file
        if length==-1:
            length = min(MAX_READ, self.length - self.fpos + 1)
        
        if debug:
            print("read: fpos={}  length={}".format(self.fpos,length))
        # Can we satisfy from the front cache?
        if self.fpos < CACHE_SIZE and self.fpos+length < CACHE_SIZE:
            if debug:print("front cache")
            buf = self.frontcache[self.fpos:self.fpos+length]
            self.fpos += len(buf)
            if debug:print("return 1: buf=",buf)
            return buf

        # Can we satisfy from the back cache?
        if self.backcache and (self.length - CACHE_SIZE < self.fpos):
            if debug:print("back cache")
            buf = self.backcache[self.fpos - self.backcache_start:self.fpos - self.backcache_start + length]
            self.fpos += len(buf)
            if debug:print("return 2: buf=",buf)
            return buf

        buf = self._readrange(self.fpos, length)
        self.fpos += len(buf)
        if debug:print("return 3: buf=",buf)
        return buf

    def seek(self,offset,whence=0):
        if debug:print("seek({},{})".format(offset,whence))
        if whence==0:
            self.fpos = offset
        elif whence==1:
            self.fpos += offset
        elif whence==2:
            self.fpos = self.length + offset
        else:
            raise RuntimeError("whence={}".format(whence))
        if debug:print("   ={}  (self.length={})".format(self.fpos,self.length))

    def tell(self):
        return self.fpos

    def write(self):
        raise RuntimeError("Write not supported")

    def flush(self):
        raise RuntimeError("Flush not supported")

    def close(self):
        return


