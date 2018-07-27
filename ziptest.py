import zipfile

class FakeFile:
    """Like a real file, but prints what's happening."""
    def __init__(self,name):
        self.name = name
        self.fp  = open(name,"rb")

    def __repr__(self):
        return "FakeFile<name:{} fp:{}>".format(self.name,self.fp)

    def read(self,len=-1):
        print("read({})".format(len))
        return self.fp.read(len)

    def seek(self,offset,whence):
        print("will seek {},{}".format(offset,whence))
        try:
            r = self.fp.seek(offset,whence)
        except Exception as e:
            print("Exception: ",e)
        print("seek({},{})={}".format(offset,whence,r))
        return r

    def tell(self):
        r = self.fp.tell()
        print("tell()={}".format(r))
        return r

    def write(self):
        raise RuntimeError("Write not supported")

    def flush(self):
        raise RuntimeError("Flush not supported")

    def close(self):
        print("closed")
        return self.fp.close()


# Try with
# aws s3api get-object --bucket my_s3_bucket --key s3_folder/file.txt --range bytes=0-1000000 tmp_file.txt && head tmp_file.txt

if __name__=="__main__":
    ff = FakeFile("/Users/simsong/Downloads/OperaSetup.zip")
    zf = zipfile.ZipFile(ff, mode='r', allowZip64=True)
    print("name list:",zf.namelist())
    
