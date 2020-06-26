import os
import sys

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))

from ctools.schema.recode import Recode

def test_Recode():
    r = Recode("name","A[a] = B[b]")
    assert r.name            == "name"
    assert r.dest_table_name == "A"
    assert r.dest_table_var  == "a"
    assert r.statement       == "A[a] = B[b]"

    r = Recode("name","A[a]=B[b]")
    assert r.name            == "name"
    assert r.dest_table_name == "A"
    assert r.dest_table_var  == "a"
    assert r.statement       == "A[a]=B[b]"
    

