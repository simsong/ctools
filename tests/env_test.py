import os
import os.path
import ctools.env
import sys
import io
from os.path import dirname,basename,abspath


from os.path import dirname

sys.path.append(dirname(dirname(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
import ctools.env as env

ETC_TEST_FILE = '/etc/hosts'    # a file that should always be present
ENV_TEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "env_test_file.bash")
TEST_FILES_DIR = os.path.join(dirname(abspath(__file__)), "test_files")
TEST_BASH_PATH = os.path.join(TEST_FILES_DIR,"env_test.sh")

test_config = {"*": {"FOO":"default_foo",
                     "BAR":"default_bar"},
               "E1": {"FOO":"E1_foo",
                      "BAZ":"E1_baz",
                      "BINK":{"A":"a",
                              "B":"b" }}}


def test_get_env():
    assert os.path.exists(ENV_TEST_FILE)
    d = ctools.env.get_vars(ENV_TEST_FILE)
    assert len(d)==2
    assert d['FOO'] == 'bar'
    assert d['NOFOO'] == 'nope'

def test_get_env2():
    ret = env.get_env(TEST_BASH_PATH)
    assert ret['FIRST']=='1'
    assert ret['FILE']=='the file'
    assert os.environ['FIRST'] == '1'
    assert os.environ['FILE'] == 'the file'

    ret2 = env.get_env(profile_dir=dirname(TEST_BASH_PATH), prefix='ctools')
    print(ret2)
    assert ret2['CTOOLS']=='YES'


def test_dump():
    os.environ['FOO']='BAR'
    f = io.StringIO()
    env.dump(f)
    assert "= ENV =" in f.getvalue()
    assert "FOO=BAR" in f.getvalue()



def test_searchFile():
    env_in_test_files_dir = os.path.join(TEST_FILES_DIR,"env.py")
    assert env.JSONConfigReader.searchFile(env_in_test_files_dir) == abspath(env.__file__)
    # fix these to use a file known to exist
    #env_in_etc            = "/etc/env.py"
    #assert env.JSONConfigReader.searchFile(env_in_etc) == abspath(env.__file__)
    #assert env.JSONConfigReader.searchFile("/etc/motd") == "/etc/motd"


def test_JSONConfigReader():
    cr = env.JSONConfigReader(config=test_config)
    assert cr.get_config("FOO","E1")=="E1_foo"
    assert cr.get_config("BAR","E1")=="default_bar"
    assert cr.get_config("BAZ","E1")=="E1_baz"
    assert cr.get_config("FOO","E2")=="default_foo"
    assert cr.get_config("BAR","E2")=="default_bar"
    assert cr.get_config("BINK.A","E1")=="a"

    config_in_test_dir = os.path.join(TEST_FILES_DIR,"test_config.json")
    cr = env.JSONConfigReader(path=config_in_test_dir)
    assert cr.get_config("NAME","F") == "ALPHA"
