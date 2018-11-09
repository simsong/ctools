#!/usr/bin/env python3
#

import os

from ctools.hiearchical_configparser import HiearchicalConfigParser


MYDIR=os.path.dirname(__file__)

def toast_hiearchical_configparser1():
    hcf = HiearchicalConfigParser()
    hcf.read(MYDIR+"/hcf_file1.ini")
    assert hcf['a']['color']=='file1-a'
    assert hcf['a']['second']=='file2-a'
    assert hcf['b']['color']=='file1-b'
    assert 'second' not in hcf['b']
    
    
def test_hiearchical_configparser2():
    hcf = HiearchicalConfigParser()
    hcf.read(MYDIR+"/hcf_file3.ini")
    print("and we got:")
    hcf.write(open("/dev/stdout","w"))
    assert hcf['a']['color']=='file2-a'
    assert hcf['a']['second']=='file2-a'
    assert hcf['b']['color']=='file2-b'
    assert hcf['b']['second']=='file2-b'
    assert hcf['c']['color']=='file2-c'
    assert hcf['c']['second']=='file2-c'
    assert hcf['d']['color']=='file1-d'
    
    hcf = HiearchicalConfigParser()
    hcf.read(MYDIR+"/hcf_file4a.ini")
    assert hcf['a']['color']=='hcf_file4a'
    
    
