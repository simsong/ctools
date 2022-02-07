#!/usr/bin/env python3
#
"""Demonstrate running Spark, logging on the nodes, and collecting the log messages on the head-end"""

from ctools import clogging
from ctools import cspark
import sys
import os
import socket
import logging
import json

# Because this is a demo, it's not really part of the ctools package.
# So we need to manually add the parent directory to the path, so we can use it.

from os.path import abspath,dirname


sys.path.append(dirname(abspath(__file__)))

import cspark
import clogging

__author__ = "Simson L. Garfinkel"
__version__ = "0.0.1"


def applicationId():
    """Return the Yarn applicationID.
    This only works within a Yarn container, which means in a mapper or reducer.
    """
    try:
        return "_".join(['application'] + os.environ['CONTAINER_ID'].split("_")[1:3])
    except KeyError:
        return "unknown"

def square(x):
    """This is the map function. It's going to run on the executors.
    Log the hostname, the PID and X as a JSON object"""
    from pyspark import SparkContext
    clogging.setup(level=logging.INFO, syslog='True')
    logging.info(json.dumps({'hostname': socket.gethostname(),
                             'pid': os.getpid(), 'x': x, 'func': 'square', 'applicationId': applicationId()}))
    return x *x

def myadder(x, y):
    """This is the map function. It's going to run on the executors.
    Log the hostname, the PID and X as a JSON object"""
    from pyspark import SparkContext
    clogging.setup(level=logging.INFO, syslog='True')
    logging.info(json.dumps({'hostname': socket.gethostname(), 'pid': os.getpid(),
                             'x': x, 'y': y, 'func': 'myadder', 'applicationId': applicationId()}))
    return x +y


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    args = parser.parse_args()

    if not cspark.spark_available():
        print("Spark is not available.")
        exit(0)

    print("Running spark with 16 executors.... My PID is {}".format(os.getpid()))
    pyfiles = [clogging.__file__, cspark.__file__]

    sc = cspark.spark_session(num_executors=16, pyfiles=pyfiles).sparkContext
    print("Spark Context Obtained. sc={}  My PID is now {}".format(sc, os.getpid()))
    print("application id:", sc.applicationId)

    # Initialize logging on the head-end.
    # This is done after the Spark context is acquired, but it could be done before.
    clogging.setup(level=logging.INFO, syslog=True, filename='demo_logfile.log')

    # Count the squares of the numbers 1..1000
    result = sc.parallelize(range(1, 1001)).map(square).reduce(myadder)

    print("The numbers 1..1000 square add to {}".format(result))

    print("Dumping the lines in the logfile that have my applicationId and collect all of the json objects:")
    objs = []
    for line in open("/var/log/local1.log"):
        if sc.applicationId in line:
            print(line, end='')
            objs.append(json.loads(line[line.find('{'):]))

    print("Here are all the json objects with x=50:")
    for obj in objs:
        if obj['x']==50:
            print(obj)

    print("We're still running under spark-submit. The parent program will exit as soon as the child does.")
    exit(0)
