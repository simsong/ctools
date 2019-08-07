#!/usr/bin/env python3

#
# tools for implementing locking of script

import sys
import os
import fcntl
import logging

def lock_script(scriptpath=sys.argv[0]):
    """Lock the script so that only one copy can run at once"""
    try:
        fd = os.open(scriptpath,os.O_RDONLY)
    except FileNotFound as f:
        raise FileNotFound("Could not find script at {}".format(scriptpath))

    if fd>0:
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB) # non-blocking
        except IOError:
            raise RuntimeError("Could not acquire lock")
        return fd
    raise RuntimeError("Could not open {}".format(scriptpath))
