#!/usr/bin/env python3
#

import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ctools.hierarchical_configparser import HierarchicalConfigParser, fixpath


MYDIR=os.path.dirname(__file__)


def test_fixpath():
    assert fixpath("/a/b/c", "/a/b") == "/a/b"
    assert fixpath("/a/b/c", "b") == os.path.join("/a/b","b")

def test_hierarchical_configparser1():
    hcf = HierarchicalConfigParser(debug=True)
    hcf.read(MYDIR + "/hcf_file2.ini")
    assert sorted(list(hcf.sections())) == ['a', 'b', 'c']
    assert hcf['a']['color'] == 'file2-a'
    assert hcf['a']['second'] == 'file2-a'
    assert hcf['b']['color'] == 'file2-b'
    assert hcf['b']['second'] == 'file2-b'
    assert hcf['c']['color'] == 'file2-c'
    assert hcf['c']['second'] == 'file2-c'

def test_hierarchical_configparser2():
    fname = MYDIR + "/hcf_file1.ini"  # includes hcf_file2.ini as a default
    assert os.path.exists(fname)
    hcf = HierarchicalConfigParser()
    hcf.read(fname)
    # Validate what's in hcf_file1.ini
    assert hcf['a']['INCLUDE'] == 'hcf_file2.ini'
    assert hcf['a']['color'] == 'file1-a'
    assert hcf['b']['color'] == 'file1-b'

    # Validate what was included in section 'a' and was not overwritten
    assert hcf['a']['second'] == 'file2-a'

    # Validate that additional tag in section 'b' was not included (because include is not in DEFAULT)
    assert 'second' not in hcf['b']

    # Validate that section 'c' was not included
    assert 'c' not in hcf.sections()

def test_hierarchical_configparser3():
    fname = MYDIR + "/hcf_file3.ini"
    print("Original config file:")
    print(open(fname,"r").read())
    print("--------------------------\n\n")
    hcf = HierarchicalConfigParser(debug=True)
    hcf.read(fname)
    print("and we got:")
    hcf.write(sys.stdout)

    # The include is in DEFAULT, so we start with ALL of the tags in hcf_file3.ini:
    assert hcf['c']['sound'] == 'file3-c'
    assert hcf['d']['color'] == 'file3-d'

    # and then we get those in hcf_file2 that were not overwritten
    assert hcf['a']['color'] == 'file2-a'
    assert hcf['a']['second'] == 'file2-a'
    assert hcf['b']['color'] == 'file2-b'
    assert hcf['b']['second'] == 'file2-b'
    assert hcf['c']['color'] == 'file2-c'
    assert hcf['c']['second'] == 'file2-c'
    print("Explaination:")
    hcf.explain(sys.stdout)

def test_hierarchical_configparser4():
    fname = MYDIR + "/hcf_file4.ini"
    hcf = HierarchicalConfigParser(debug=True)
    hcf.read(fname)
    print("and we got:")
    hcf.write(sys.stdout)
    assert hcf['a']['filename'] == 'hcf_file4'
    assert hcf['b']['filename'] == 'hcf_file5'
    assert hcf['c']['filename'] == 'hcf_file6'
    assert hcf['d']['filename'] == 'hcf_file6'
    print("Explaination:")
    hcf.explain(sys.stdout)

def test_hierarchical_configparser5():
    fname = MYDIR + "/hcf_filea.ini"
    hcf = HierarchicalConfigParser(debug=True)
    hcf.read(fname)
    print("and we got:")
    hcf.write(sys.stdout)
    hcf.explain()

    # what was originally in hcf_filea.ini:
    assert hcf['a']['file']=='hcf_filea'

    # what was included in [a] from fileb.ini
    assert hcf['a']['name']=='hcf_fileb'

    # what was included from [default] include filec.ini
    assert hcf['b']['file']=='hcf_filec'
    assert hcf['c']['file']=='hcf_filec'
    assert hcf['d']['file']=='hcf_filed'
    


def test_hierarchical_configparser6():
    fname = MYDIR + "/hcf_test/child/hcf_file6.ini"
    hcf = HierarchicalConfigParser(debug=True)
    hcf.read(fname)
    print("and we got:")
    hcf.write(sys.stdout)
    hcf.explain()

    # what was originally in child/hcf_file4:
    assert hcf['level']['location'] == 'child'

    # child has a section [file5] that includes ../../hcf_file5.ini which has a file5 section
    assert hcf['file5']['special'] == '10'

    # child [default] includes ../hcf_file6.ini:
    assert hcf['parent']['children'] == '1'

    # ../hcf_file6.ini has a DEFAULT include to ../hcf_file5.ini:
    assert hcf['b']['filename'] == 'hcf_file5'

    # ../hcf_file5.ini has a DEFAULT include to hcf_file6.ini
    assert hcf['a']['filename'] == 'hcf_file6'
    assert hcf['c']['filename'] == 'hcf_file6'
    assert hcf['d']['filename'] == 'hcf_file6'
    print("Explaination:")
    hcf.explain(sys.stdout)
    
