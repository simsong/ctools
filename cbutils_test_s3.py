#!/usr/bin/env python3
# Test S3 code

from cbutils import *

def test_s3open():
    path = "s3://uscb-decennial-ite-das/motd"

    for line in s3open(path,"r"):
        print("> ",line)


if __name__=="__main__":
    test_s3open()
