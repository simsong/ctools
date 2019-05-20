import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__),"../.."))

import ctools.schema as schema
from ctools.schema.variable import Variable

def test_Variable():
    v = Variable( name = 'test',
                  column = 10,
                  width = 2,
                  vtype = schema.TYPE_VARCHAR) 
    
    assert(v.width==2)
    


