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


def file_lock(lockfile, block=True):
    """Lock the script so that only one copy can run at once"""
    try:
        fd = os.open(lockfile, os.O_RDONLY)
    except FileNotFoundError as f:
        raise FileNotFoundError("Could not find script at {}".format(lockfile))

    if fd > 0:
        try:
            flags = fcntl.LOCK_EX
            if not block:
                flags |= fcntl.LOCK_NB
            fcntl.flock(fd, flags)
        except IOError:
            raise RuntimeError(f"Could not acquire lock on {lockfile}")
        return fd
    raise RuntimeError(f"Could not open {lockfile}")


def lock_script(lockfile=sys.argv[0]):
    return file_lock(lockfile, block=False)
