# Some tests for tytable

import sys
import os
import os.path

sys.path.append( os.path.join( os.path.dirname(__file__), "../.."))

from ctools.tydoc import *

def test_ttable():
    a = ttable()
    a.add_head(['Head One','Head Two'])
    a.add_data([1,2])
    a.add_data(['foo','bar'])
    print( a.typeset(mode=LATEX ))
    print( a.typeset(mode=HTML ))

    a.add_data(['foo','bar'],annotations=['\\cellcolor{blue}',''])
    assert 'blue' in a.typeset(mode=LATEX)

def test_tytable():
    a = tytable()
    a.add_row([1,2,3])
    a.add_row(['a','b','c'])
    a.add_row([1,2,3,4])
    a.add_row(['a','b','c','d','e'])
    assert len(a.rows()) == 4
    assert a.max_cols() == 5
    
