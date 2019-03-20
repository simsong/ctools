# Some tests for tytable

import sys
import os
import os.path

<<<<<<< HEAD
sys.path.append( os.path.join( os.path.dirname(__file__), "../.."))

from ctools.tydoc import *
=======
from ctools.tytable import ttable, tytable
>>>>>>> b88d626cc2e368b99697ec6b9bd56af7f6fbb3ec

def test_ttable():
    a = ttable()
    a.add_head(['Head One','Head Two'])
    a.add_data([1,2])
    a.add_data(['foo','bar'])
    print( a.typeset(mode=a.LATEX ))
    print( a.typeset(mode=a.HTML ))

    a.add_data(['foo','bar'],annotations=['\\cellcolor{blue}',''])
    assert 'blue' in a.typeset(mode=a.LATEX)

def test_tytable():
    a = tytable()
<<<<<<< HEAD
    a.add_row([1,2,3])
    a.add_row(['a','b','c'])
    a.add_row([1,2,3,4])
    a.add_row(['a','b','c','d','e'])
    assert len(a.rows()) == 4
    assert a.max_cols() == 5
=======
    a.add_row('td', [1,2,3])
    a.add_row('td', ['a','b','c'])
    a.add_row('td', [1,2,3,4])
    a.add_row('td', ['a','b','c','d','e'])
    assert a.nrows()==4
    assert a.ncols()==4
>>>>>>> b88d626cc2e368b99697ec6b9bd56af7f6fbb3ec
    
