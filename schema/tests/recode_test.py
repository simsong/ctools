import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__),"../.."))

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
    

