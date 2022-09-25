"""
gzfile test
"""

import sys
import py.test
import os
import os.path
import logging
import time
import platform
import warnings
import platform
from os.path import dirname,basename,abspath

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

from ctools.gzfile import GZFile

TEST_STRING="this is a test\n"

def test_gzfile():
    if platform.system()=='Windows':
        return

    with GZFile("test.gz","w") as f:
        f.write(TEST_STRING)

    with open("test.gz","rb") as f:
        data = f.read()
    assert len(data) > 0
    assert len(data) != len(TEST_STRING)

    with GZFile("test.gz","r") as f:
        data = f.read()
    assert data==TEST_STRING
    os.unlink("test.gz")
