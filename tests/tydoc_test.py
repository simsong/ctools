# Some tests for tytable

from ctools.latex_tools import run_latex, no_latex, LatexException
from ctools.tydoc import tydoc, TyTag, tytable, ET, tytable, ATTRIB_ALIGN, ALIGN_CENTER, \
    ALIGN_RIGHT, OPTION_TABLE, OPTION_LONGTABLE, TAG_X_TOC, TAG_BODY, TAG_H1, TAG_A, TAG_TD
import sys
import os
import os.path
import tempfile
import warnings

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))


def test_tytag_option():
    t = TyTag('demo')
    t.set_option("FOO")
    assert t.option("FOO") == True
    assert t.option("BAR") == False
    t.set_option("BAR")
    assert t.option("FOO") == True
    assert t.option("BAR") == True
    t.clear_option("FOO")
    assert t.option("FOO") == False
    assert t.option("BAR") == True


def test_tytable_access():
    """Make sure construction and access methods work properly"""
    t = tytable()
    t.add_head(['x', 'x-squared', 'x-cubed'])
    t.add_data([1, 1, 1])
    t.add_data([2, 4, 8])
    t.add_data([3, 9, 27])
    for row in t.rows():
        s = ET.tostring(row, encoding='unicode')
        print(s)
    assert t.get_cell(0, 1).text == 'x-squared'
    assert float(t.get_cell(1, 1).text) == 1
    assert float(t.get_cell(2, 1).text) == 4
    assert float(t.get_cell(3, 1).text) == 9


def test_tytable_attribs():
    d2 = tytable()
    d2.set_option(OPTION_LONGTABLE)
    d2.add_head(['State', 'Abbreviation', 'Population'],
                cell_attribs={ATTRIB_ALIGN: ALIGN_CENTER})
    d2.add_data(['Virginia', 'VA', 8001045],
                cell_attribs=[{}, {ATTRIB_ALIGN: ALIGN_CENTER}, {ATTRIB_ALIGN: ALIGN_RIGHT}])
    d2.add_data(['California', 'CA', 37252895],
                cell_attribs=[{}, {ATTRIB_ALIGN: ALIGN_CENTER}, {ATTRIB_ALIGN: ALIGN_RIGHT}])
    s = ET.tostring(d2, encoding='unicode')
    assert 'CENTER' in s
    assert d2.get_cell(0, 0).attrib[ATTRIB_ALIGN] == ALIGN_CENTER
    assert d2.get_cell(0, 1).attrib[ATTRIB_ALIGN] == ALIGN_CENTER
    assert d2.get_cell(0, 2).attrib[ATTRIB_ALIGN] == ALIGN_CENTER
    assert ATTRIB_ALIGN not in d2.get_cell(1, 0).attrib
    assert d2.get_cell(1, 1).attrib[ATTRIB_ALIGN] == ALIGN_CENTER
    assert d2.get_cell(1, 2).attrib[ATTRIB_ALIGN] == ALIGN_RIGHT


def test_tydoc_latex(tmpdir):
    """Create a document that tries lots of features and then make a LaTeX document and run LaTeX"""

    doc = tydoc()
    doc.h1("Table demo")

    d2 = doc.table()
    d2.set_option(OPTION_TABLE)
    d2.add_head(['State', 'Abbreviation', 'Population'])
    d2.add_data(['Virginia', 'VA', 8001045])
    d2.add_data(['California', 'CA', 37252895])

    d2 = doc.table()
    d2.set_option(OPTION_LONGTABLE)
    d2.add_head(['State', 'Abbreviation', 'Population'])
    d2.add_data(['Virginia', 'VA', 8001045])
    d2.add_data(['California', 'CA', 37252895])

    doc.save(os.path.join(tmpdir, "tydoc.tex"), format="latex")

    if no_latex():
        warnings.warn("Cannot run LaTeX tests")
        return
    try:
        run_latex(os.path.join(tmpdir, "tydoc.tex"))
    except LatexException as e:
        warnings.warn("LatexException: "+str(e))


def test_tydoc_toc():
    """Test the Tydoc table of contents feature."""
    doc = tydoc()
    doc.h1("First Head1")
    doc.p("blah blah blah")
    doc.h1("Second Head1 2")
    doc.p("blah blah blah")
    doc.h2("Head 2.1")
    doc.p("blah blah blah")
    doc.h2("Head 2.2")
    doc.p("blah blah blah")
    doc.h3("Head 2.2.1")
    doc.p("blah blah blah")
    doc.h1("Third Head1 3")
    doc.p("blah blah blah")

    # Add a toc
    doc.insert_toc()

    # Make sure that the TOC has a pointer to the first H1
    print(doc.prettyprint())
    key = f".//{TAG_X_TOC}"
    tocs = doc.findall(key)
    assert len(tocs) == 1
    toc = tocs[0]

    h1s = doc.findall(".//{}/{}".format(TAG_BODY, TAG_H1))
    assert len(h1s) == 3
    h1 = h1s[0]

    # Make sure that they both have the same ID
    id1 = toc.find('.//{}'.format(TAG_A)).attrib['HREF']
    id2 = h1.find('.//{}'.format(TAG_A)).attrib['NAME']

    assert id1 == ('#'+id2)


def test_tytable_autoid():
    """test the autoid feature"""
    t = tytable()
    t.add_head(['foo', 'bar', 'baz'], col_auto_ids=['foo', 'bar', 'baz'])
    t.add_data([1, 2, 3], row_auto_id="row1")
    t.add_data([2, 3, 4], row_auto_id="row2")
    t.add_data([5, 6, 7], row_auto_id="row3")
    with tempfile.NamedTemporaryFile(suffix='.autoid.html', mode='w') as tf:
        t.save(tf, format="html")
    # Should read it and do something with it here.


def test_tytable_colspan():
    """test the colspan feature"""
    t = tytable()
    wide_cell = TyTag(TAG_TD, attrib={'COLSPAN': 2}, text='Wide Column')
    t.add_head(['foo', 'bar', 'baz', 'bif'],
               col_auto_ids=['foo', 'bar', 'baz', 'bif'])
    t.add_data([1, 2, 3, 4], row_auto_id="row1")
    t.add_data([2, wide_cell, 5], row_auto_id="row2")
    t.add_data([3, 4, 5, 6], row_auto_id="row3")

    # Make sure that the colspan is working
    assert t.get_cell(0, 0).text == 'foo'
    assert t.get_cell(0, 1).text == 'bar'
    assert t.get_cell(0, 2).text == 'baz'
    assert t.get_cell(0, 3).text == 'bif'

    assert t.get_cell(1, 0).text == '1'
    assert t.get_cell(1, 1).text == '2'
    assert t.get_cell(1, 2).text == '3'
    assert t.get_cell(1, 3).text == '4'

    assert t.get_cell(2, 0).text == '2'
    assert t.get_cell(2, 1).text == 'Wide Column'
    assert t.get_cell(2, 2).text == None
    assert t.get_cell(2, 3).text == '5'

    with tempfile.NamedTemporaryFile(suffix='.html', mode='w') as tf:
        t.save(tf, format="html")
    with tempfile.NamedTemporaryFile(suffix='.json', mode='w') as tf:
        t.save(tf, format="json")
    # Should read it and do something with it here.
