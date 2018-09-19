#!/usr/bin/env python3
# Test S3 code

import os
import sys
import warnings
from ctools.s3 import *

def test_s3open():
    if "EC2_HOME" in os.environ:
        path = "s3://uscb-decennial-ite-das/motd"

        for line in s3open(path,"r"):
            print("> ",line)
    else:
        warnings.warn("test_s3open only runs on AWS EC2 computers")


if __name__=="__main__":
    test_s3open()
