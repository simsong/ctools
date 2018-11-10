#!/usr/bin/env python3
#

import os

from ctools.hiearchical_configparser import HiearchicalConfigParser


MYDIR=os.path.dirname(__file__)

def text_fixpath():
    fixpath("/a/b/c","/a/b")=="/a/b"
    fixpath("/a/b/c","b")=="/a/b/b"
    
def test_hiearchical_configparser1():
    hcf = HiearchicalConfigParser()
    hcf.read(MYDIR+"/hcf_file2.ini")
    assert sorted(list(hcf.sections()))==['a','b','c']
    assert hcf['a']['color']=='file2-a'
    assert hcf['a']['second']=='file2-a'
    assert hcf['b']['color']=='file2-b'
    assert hcf['b']['second']=='file2-b'
    assert hcf['c']['color']=='file2-c'
    assert hcf['c']['second']=='file2-c'
    
def test_hiearchical_configparser2():
    fname = MYDIR+"/hcf_file1.ini" # includes hcf_file2.ini as a default
    assert os.path.exists(fname)
    hcf = HiearchicalConfigParser()
    hcf.read(fname)
    # Validate what's in hcf_file1.ini
    assert hcf['a']['INCLUDE']=='hcf_file2.ini'
    assert hcf['a']['color']=='file1-a'
    assert hcf['b']['color']=='file1-b'

    # Validate what was included in section 'a' and was not overwritten
    assert hcf['a']['second']=='file2-a'

    # Validate that additional tag in section 'b' was not included
    assert 'second' not in hcf['b']

    # Validate that section 'c' was not included
    assert 'c' not in hcf.sections()
    
    
def test_hiearchical_configparser3():
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
    
