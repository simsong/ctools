#!/usr/bin/env python3
#

import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ctools.hierarchical_configparser import *

MYDIR=os.path.dirname(__file__)


def fname(path):
    return os.path.join( os.path.abspath(MYDIR),path)


def fcontents(path):
    return open(fname(path),"r").read()


HCF_FILE7_NAME=fname("hcf_file7.ini")
HCF_FILE8_NAME=fname("hcf_file8.ini")
HCF_FILED_NAME=fname("hcf_filed.ini")
HCF_FILE7_CONTENTS_HEADER=";\n; test case 7:\n; just include filed\n"
HCF_FILE7_CONTENTS_FLATTENED=fcontents("hcf_file7_flattened.ini")
HCF_FILE8_CONTENTS_FLATTENED=fcontents("hcf_file8_flattened.ini")
HCF_FILED_CONTENTS=fcontents("hcf_filed.ini")
HCF_FILED_CONTENTS_ONLYB="[b]\nname=hcf_filed_section_b\n\n"


def test_include_re():
    m = INCLUDE_RE.search("INCLUDE=foobar")
    assert m.group(1)=="foobar"

    m = INCLUDE_RE.search("     INCLUDE = foobar        ;lovely comments")
    assert m.group(1)=="foobar"

    m = INCLUDE_RE.search("     INCLUDE = foo/bar        ;lovely comments")
    assert m.group(1)=="foo/bar"


def test_getOption():
    assert getOption("foo bar")==None
    assert getOption("foo: bar")=='foo'
    assert getOption("foo : bar")=='foo'
    assert getOption("foo = bar")=='foo'
    assert getOption(" foo = bar")=='foo'
    assert getOption("; foo = bar")==None

def test_getAllOptions():
    allOptions = getAllOptions(["a=1\n","b=2\n","c=3"])
    assert list(sorted(allOptions))==['a','b','c']

def test_no_includes():
    hcp = HCP()
    hcp.read( HCF_FILED_NAME )
    a = hcp.asString()
    b = HCF_FILED_CONTENTS
    print("a=",a)
    print("b=",b)
    print(len(a),len(b))
    assert hcp.asString() == HCF_FILED_CONTENTS
    assert len(hcp.sections)==6
    assert list(hcp.sections.keys())==['','a','b','c','d','e']

    hcp = HCP()
    hcp.read( HCF_FILED_NAME ,onlySection='b')
    assert hcp.asString() == HCF_FILED_CONTENTS_ONLYB

    print("sections=",hcp.sections)
    assert len(hcp.sections)==1
    assert list(hcp.sections.keys())==['b']


def test_default_include():
    hcp = HCP()
    hcp.read( HCF_FILE7_NAME )
    print("hcp.asString:")
    print(hcp.asString())
    assert hcp.asString() == HCF_FILE7_CONTENTS_FLATTENED


def test_include_one_section():
    hcp = HCP()
    hcp.read( HCF_FILE8_NAME )
    assert hcp.asString() == HCF_FILE8_CONTENTS_FLATTENED


def test_hierarchical_configparser1():
    hcf = HierarchicalConfigParser()
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

@pytest.mark.skip
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

@pytest.mark.skip
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

@pytest.mark.skip
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


@pytest.mark.skip
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
