#!/usr/bin/env python3
"""
Tool for implementing locking of script
To assure that only one copy of a script is running, insert this in __main__:
    import ctools.lock
    ctools.lock.lock_script()

If a copy of the script is already running, a RuntimeError will be generated.
"""


import sys
import os
import fcntl
import logging

def lock_script(scriptpath=sys.argv[0]):
    """Lock the script so that only one copy can run at once"""
    try:
        fd = os.open(scriptpath, os.O_RDONLY)
    except FileNotFoundError as f:
        raise FileNotFoundError("Could not find script at {}".format(scriptpath))

    if fd>0:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX |fcntl.LOCK_NB)  # non-blocking
        except IOError:
            raise RuntimeError("Could not acquire lock")
        return fd
    raise RuntimeError("Could not open {}".format(scriptpath))
