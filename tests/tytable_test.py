# Some tests for tytable

from ctools.tytable import ttable
from ctools.tydoc import tytable
import sys
import os
import os.path

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))


def test_ttable():
    a = ttable()
    a.add_head(['Head One', 'Head Two'])
    a.add_data([1, 2])
    a.add_data(['foo', 'bar'])
    print(a.typeset(mode=a.LATEX))
    print(a.typeset(mode=a.HTML))

    a.add_data(['foo', 'bar'], annotations=['\\cellcolor{blue}', ''])
    assert 'blue' in a.typeset(mode=a.LATEX)


def test_tytable():
    a = tytable()
    a.add_data([1, 2, 3])
    a.add_data(['a', 'b', 'c'])
    a.add_data([1, 2, 3, 4])
    a.add_data(['a', 'b', 'c', 'd', 'e'])
    assert len(a.rows()) == 4
    assert a.max_cols() == 5
