import os
import os.path
import ctools.env

ENV_TEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "env_test_file.bash")

def test_get_env():
    assert os.path.exists(ENV_TEST_FILE)
    d = ctools.env.get_vars(ENV_TEST_FILE)
    assert len(d)==2
    assert d['FOO'] == 'bar'
    assert d['NOFOO'] == 'nope'
