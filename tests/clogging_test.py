#!/usr/bin/env python3
#
# clogging_test.py:
#
# various test functions for the logging


import sys
import py.test
import os
import os.path
import logging
import time

sys.path.append( os.path.join(os.path.dirname(__file__), ".."))
sys.path.append( os.path.join(os.path.dirname(__file__), "../.."))

import ctools.clogging 

def test_logging_to_syslog():
    ctools.clogging.setup(level='INFO',syslog=True)
    nonce = str(time.time())
    logging.info("Logging at t={}".format(nonce))
    # Wait a few miliseconds for the nonce to appear in the logfile
    time.sleep(.01)
    # Look for the nonce
    count = 0
    for line in open("/var/log/local1.log"):
        if nonce in line:
            print(line)
            count += 1
    assert count==1
    ctools.clogging.shutdown()

    
