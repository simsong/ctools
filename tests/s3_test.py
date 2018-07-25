#!/usr/bin/env python3
# Test S3 code

import os
import sys

sys.path.append( os.path.join(os.path.dirname(__file__), ".."))
sys.path.append( os.path.join(os.path.dirname(__file__), "../.."))

from ctools.s3 import s3open

def test_s3open():
    path = "s3://uscb-decennial-ite-das/motd"

    for line in s3open(path,"r"):
        print("> ",line)


if __name__=="__main__":
    test_s3open()
