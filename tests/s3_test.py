3#!/usr/bin/env python3
# Test S3 code

import os
import sys
import warnings
import pytest
import uuid
import logging
import zipfile

from os.path import abspath
from os.path import dirname

MY_DIR = dirname(abspath(__file__))
TEST_FILE_DIR = os.path.join(MY_DIR,'test_files')
PARENT_DIR = dirname(MY_DIR)

if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

import ctools.s3 as s3

MOTD = 'etc/motd'
TEST_STRING  = "As it is written " + str(os.getpid()) + "\n"
TEST_S3_FILE = "Examples/testfile.txt"
TEST_ZIPFILE = os.path.join(TEST_FILE_DIR,'testfile.zip')

def is_aws():
    return ("EC2_HOME" in os.environ or
            os.path.exists("/etc/amazon"))

def s3root():
    """S3 bucket for testing"""
    if "TEST_S3ROOT" in os.environ:
        return os.environ['TEST_S3ROOT']
    elif "DAS_S3ROOT" in os.environ:
        return os.environ['DAS_S3ROOT']
    elif "S3ROOT" in os.environ:
        return os.environ['S3ROOT']
    else:
        return  None

@pytest.fixture
def s3_tempfile():
    path = os.path.join( s3root(), f"tmp/tmp.{uuid.uuid4()}")
    logging.info("s3_tempfile: %s",path)
    yield path
    s3.s3rm(path)

@pytest.mark.skipif(not is_aws(),reason='Not running on AWS')
@pytest.mark.skipif(s3root() is None,reason='No S3ROOT defined')
def test_s3open(s3_tempfile):
    # Make sure attempt to read a file that doesn't exist gives a FileNotFound error
    got_exception = True
    try:
        f = s3.s3open("bad path")
        got_exception = False
    except ValueError as e:
        pass
    if got_exception==False:
        raise RuntimeError("should have gotten exception for bad path")

    # Make sure s3open works in a variety of approaches
    # Reading s3open as an iterator
    val1 = ""
    for line in s3.s3open( s3_tempfile, "r"):
        val1 += line

    # Reading s3open with .read():
    f = s3.s3open( s3_tempfile, "r")
    val2 = f.read()

    # Reading s3open with a context manager
    with s3.s3open( s3_tempfile,"r") as f:
        val3 = f.read()

    assert val1==val2==val3


@pytest.mark.skipif(not is_aws(),reason='Not running on AWS')
@pytest.mark.skipif(s3root() is None,reason='No S3ROOT defined')
def test_s3open_write_fsync(s3_tempfile):
    """See if we s3open with the fsync option works"""

    with s3.s3open( s3_tempfile, "w", fsync=True) as f:
        f.write( TEST_STRING)
    with s3.s3open( s3_tempfile,"r") as f:
        buf = f.read()
        assert buf==TEST_STRING


@pytest.mark.skipif(not is_aws(),reason='Not running on AWS')
@pytest.mark.skipif(s3root() is None,reason='No S3ROOT defined')
def test_s3open_iter(s3_tempfile):
    with s3.s3open(s3_tempfile, "w", fsync=True) as f:
        for i in range(10):
            f.write( TEST_STRING[:-1] + str(i) + "\n")

    with s3.s3open( s3_tempfile, "r") as f:
        fl = [l for l in f]
        for i, l in enumerate(fl):
            assert l == TEST_STRING[:-1]  + str(i) + "\n"

    f = s3.s3open(s3_tempfile, "r")
    fl = [ l for l in f ]
    for i, l in enumerate(fl):
        assert l == TEST_STRING[:-1] + str(i) + "\n"


@pytest.mark.skipif(not is_aws(),reason='Not running on AWS')
@pytest.mark.skipif(s3root() is None,reason='No S3ROOT defined')
def test_s3zipfile_support(s3_tempfile):
    """See if we can read hello.txt from a zipfile we upload. This is a pretty good test."""
    with s3.s3open(s3_tempfile, 'wb', fsync=True) as f:
        f.write( open(TEST_ZIPFILE, 'rb').read() )
    zf = zipfile.ZipFile( s3.S3File(s3_tempfile))
    hf = zf.open('hello.txt')
    hello = hf.read()
    assert hello == b'Hello World!\n'

if __name__=="__main__":
    test_s3open()
    test_s3open_write_fsync()
