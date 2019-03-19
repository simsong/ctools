# Some tests for tytable

import sys
import os
import os.path

sys.path.append( os.path.join( os.path.dirname(__file__), "../.."))

from ctools.tydoc import *

def test_tytag_option():
    t = TyTag('demo')
    t.set_option("FOO")
    assert t.option("FOO")==True
    assert t.option("BAR")==False
    t.set_option("BAR")
    assert t.option("FOO")==True
    assert t.option("BAR")==True
    t.clear_option("FOO")
    assert t.option("FOO")==False
    assert t.option("BAR")==True

    
def test_tytable():
    t = tytable()
    t.add_head(['x','x-squared','x-cubed'])
    t.add_data([1,1,1])
    t.add_data([2,4,8])
    t.add_data([3,9,27])
    assert float(t.get_cell(3,1).text) == 9

