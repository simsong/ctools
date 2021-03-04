import os
import sys
from os.path import dirname,basename,abspath

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import env

TEST_BASH_FILE = os.path.join(dirname(abspath(__file__)),"test_files","env_test.sh")

def test_get_env():
    ret = env.get_env(TEST_BASH_FILE)
    assert ret['FIRST']=='1'
    assert ret['FILE']=='the file'
    assert os.environ['FIRST'] == '1'
    assert os.environ['FILE'] == 'the file'

    ret2 = env.get_env(profile_dir=dirname(TEST_BASH_FILE), prefix='ctools')
    print(ret2)
    assert ret2['CTOOLS']=='YES'
