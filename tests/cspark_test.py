import ctools.cspark as cspark
import sys
import os
import pytest
import io

from os.path import abspath
from os.path import dirname

import pytest

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))


CSPARK_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), "cspark.py")
assert os.path.exists(CSPARK_PATH)

fh_config = """
[spark]
name1.key1=value1
name2.key2: value2
"""


def test_spark_submit_cmd():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read_string(fh_config)
    cmd = cspark.spark_submit_cmd(configdict=config['spark'])
    assert "name1.key1=value1" in cmd
    assert "name2.key2=value2" in cmd

TEST_RUN_SPARK_FILENAME = 'TEST_RUN_SPARK_FILENAME'


def test_spark_submit():
    # Run a Spark job and then check to make sure we got the result.
    # To get the result back, we have to save it in a file. But we only want to call
    # NamedTemporaryFile once, so we store the temporary file name in an environment variable.
    # For the same reason, we can't open the file in truncate mode.

    return

    raise RuntimeWarning(
        """WARNING: this test can make all test suite exit, likely because of the use of os.execvp in cspark.py. See comments inline in the test""")

    if not cspark.spark_available():
        return                  # don't test if no Spark is available

    # spark-submit will run in a subprocess

    if TEST_RUN_SPARK_FILENAME not in os.environ:
        import tempfile
        f = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        os.environ[TEST_RUN_SPARK_FILENAME] = f.name
        f.close()

    """
    redo this so that it creates a file and submits it with spark-submit.

    with open(os.environ[TEST_RUN_SPARK_FILENAME], "w+") as f:
        if cspark.spark_submit(logLevel='error',pyfiles=[CSPARK_PATH], argv=[__file__]):
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.appName("cspark_test:test_run_spark").getOrCreate()
            import operator
            mysum = spark.sparkContext.parallelize(range(1000000)).reduce(operator.add)
            f.truncate(0)
            f.write("{}\n".format(mysum))

            # Not sure what Simson tried to do here, but the file should not be closed,
            # because it is read from later. Neither there should be any exit from the program,
            # otherwise the test just exits (and the whole suite of unit tests ends to)
            #
            # It used to work before, but now doesn't, apparently, after changing
            # of the subprocess call in cspark.spark_submit to os.execvp

            # Commenting them out fixes the run in standalone run with python,
            # but when run from pytest it still exits.
            #
            # My guess is that it is because os.exec* commands replace the processes and do not return.
            #
            # --- P.Z.

            # f.close()
            # exit(0)             # spark job is finished

            data = f.read()
            assert data=='499999500000\n'
            print("spark ran successfully")
            f.close()
    os.unlink(os.environ[TEST_RUN_SPARK_FILENAME])
    """


if __name__ == "__main__":
    # This is solely so that we can run under pytest
    # Don't remove it! You can also just run this program to see what happens
    # It should print "spark ran successfully."
    test_spark_submit_cmd()
