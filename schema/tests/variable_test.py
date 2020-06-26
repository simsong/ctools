import os
import sys

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))

import ctools.schema as schema
from ctools.schema.variable import Variable

def test_Variable():
    v = Variable( name = 'test',
                  column = 10,
                  width = 2,
                  vtype = schema.TYPE_VARCHAR) 
    
    assert(v.width==2)
    


