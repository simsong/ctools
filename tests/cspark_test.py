import py.test
from cspark import *
import io

sys.path.append( os.path.join(os.path.dirname(__file__), ".."))
sys.path.append( os.path.join(os.path.dirname(__file__), "../.."))



fh_config = io.StringIO("""
[spark]
name1.key1=value1
name2.key2: value2
""")

def test_spark_submit_cmd():
    from configparser import ConfigParser
    config = ConfigParser()
    config.readfp(fh_config)
    cmd = spark_submit_cmd(configdict=config['spark'])
    assert "name1.key1=value1" in cmd
    assert "name2.key2=value2" in cmd
    
TEST_RUN_SPARK_FILENAME='TEST_RUN_SPARK_FILENAME'
def test_run_spark():
    # Run a spark job and then check to make sure we got the result.
    # To get the result back, we have to save it in a file. But we only want to call
    # NamedTemporaryFile once, so we store the temporary file name in an environment variable.
    # For the same reason, we can't open the file in truncate mode.

    if not spark_available():
        return                  # don't test if no spark is available

    if TEST_RUN_SPARK_FILENAME not in os.environ:
        import tempfile
        f = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        os.environ[TEST_RUN_SPARK_FILENAME] = f.name
        f.close()
        
    with open(os.environ[TEST_RUN_SPARK_FILENAME], "w+") as f:
        if spark_submit(script=__file__, loglevel='error'):
            from pyspark import SparkContext, SparkConf
            from pyspark.sql import SparkSession
            import operator
            conf = SparkConf().setAppName("cspark_test:test_run_spark")
            sc   = SparkContext(conf=conf)
            sc.setLogLevel("ERROR")
            mysum = sc.parallelize(range(1000000)).reduce(operator.add)
            f.truncate(0)
            f.write("{}\n".format(mysum))
            f.close()
            exit(0)             # spark job is finished
        f.seek(0)
        data = f.read()
        assert data=='499999500000\n'
        print("spark ran successfully")
    os.unlink(os.environ[TEST_RUN_SPARK_FILENAME])


if __name__=="__main__":
    # This is solely so that we can run under py.test
    # Don't remove it! You can also just run this program to see what happens
    # It should print "spark ran successfully."
    test_run_spark()
    
