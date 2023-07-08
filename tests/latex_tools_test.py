#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Some tools for manipulating PDF files


import pytest
import os
import os.path
import sys
import logging
import warnings

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
import ctools.latex_tools as latex_tools

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")
HELLO_TEX=os.path.join(TEST_FILES_DIR,"hello.tex")
HELLO_PDF=HELLO_TEX.replace("tex","pdf")
HELLO_AUX=HELLO_TEX.replace("tex","aux")

HELLO_TEX_CONTENTS="""
\\documentclass{book}
\\begin{document}
Hello World!
\\end{document}
"""

ONEPAGE_PDF=os.path.join(TEST_FILES_DIR,"one_page.pdf")
FIVEPAGES_TEX=os.path.join(TEST_FILES_DIR,"five_pages.tex")
FIVEPAGES_PDF=os.path.join(TEST_FILES_DIR,"five_pages.pdf")
FIVEPAGES_AUX=os.path.join(TEST_FILES_DIR,"five_pages.aux")
FIVEPAGES_OUT=os.path.join(TEST_FILES_DIR,"five_pages.out")
EXTRACT_PDF=os.path.join(TEST_FILES_DIR,"extract.pdf")


def test_latex_escape():
    assert latex_tools.latex_escape(r"foo")=="foo"
    assert latex_tools.latex_escape(r"foo/bar")==r"foo/bar"
    assert latex_tools.latex_escape(r"foo\bar")==r"foo\textbackslash{}bar"

def parse_nested_braces_test():
    res = list(latex_tools.parse_nested_braces(LINE1))
    assert res == LINE1_PARSED

def test_label_parser():
    assert latex_tools.label_parser(LINE1)==("","1 Cover Sheet","1",6)
    assert latex_tools.label_parser(LINE2)==("EOF","1 Cover Sheet","1",99)

################################################################
## These tools require running LaTeX

def test_run_latex():
    if latex_tools.no_latex():
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return

    # Make sure the input file exists; if not, create it
    if not os.path.exists(HELLO_TEX):
        with open(HELLO_TEX,"w") as f:
            f.write(HELLO_TEX_CONTENTS)
    assert os.path.exists(HELLO_TEX)

    # Make sure that the output file does not exist
    if os.path.exists(HELLO_PDF):
        os.unlink(HELLO_PDF)

    # Run LaTeX. Make sure that delete_tempfiles=False leaves temp files
    try:
        latex_tools.run_latex(HELLO_TEX,delete_tempfiles=False)
    except latex_tools.LatexException as e:
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return
    assert os.path.exists(HELLO_PDF)
    assert os.path.exists(HELLO_AUX)
    os.unlink(HELLO_AUX)

    # Run LaTeX. Make sure that delete_tempfiles=False deletes the temp files
    latex_tools.run_latex(HELLO_TEX,delete_tempfiles=True)
    assert os.path.exists(HELLO_PDF)
    assert not os.path.exists(HELLO_AUX)

    # Finally, delete HELLO_TEX and HELLO_PDF
    os.unlink(HELLO_TEX)
    os.unlink(HELLO_PDF)

def test_count_pdf_pages_pypdf():
    if latex_tools.no_latex():
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return
    try:
        assert os.path.exists(ONEPAGE_PDF)   # we need this file
        assert latex_tools.count_pdf_pages_pypdf(ONEPAGE_PDF)==1
        assert os.path.exists(FIVEPAGES_PDF)   # we need this file
        assert latex_tools.count_pdf_pages_pypdf(FIVEPAGES_PDF)==5
    except (ImportError,ModuleNotFoundError):
        logging.warning("PyPDF2 is not available")
    except FileNotFoundError:
        logging.warning("no output file created")

def test_count_pdf_pages():
    if latex_tools.no_latex():
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return
    assert os.path.exists(FIVEPAGES_PDF) # we need this file
    assert not os.path.exists(FIVEPAGES_AUX) # we do not want this
    assert not os.path.exists(FIVEPAGES_OUT) # we do not want this

    try:
        pages = latex_tools.count_pdf_pages(FIVEPAGES_PDF)
    except latex_tools.LatexException as e:
        warnings.warn("LatexException: "+str(e))
        return

    assert pages==5

    assert os.path.exists(FIVEPAGES_PDF) # make sure file is still there
    assert not os.path.exists(FIVEPAGES_AUX) # we do not want this
    assert not os.path.exists(FIVEPAGES_OUT) # we do not want this

def test_inspect_pdf():
    if latex_tools.no_latex():
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return
    try:
        assert latex_tools.count_pdf_pages(FIVEPAGES_PDF) == 5
    except ModuleNotFoundError as e:
        warnings.warn("Module not found: "+str(e))
    except latex_tools.LatexException as e:
        warnings.warn("LatexException: "+str(e))

def test_extract_pdf_pages():
    if latex_tools.no_latex():
        warnings.warn("No "+latex_tools.LATEX_EXE+": Tests involving running LaTeX will not be return")
        return
    if os.path.exists(EXTRACT_PDF):
        os.unlink(EXTRACT_PDF)
    assert not os.path.exists(EXTRACT_PDF)
    assert os.path.exists(FIVEPAGES_PDF)
    if os.path.exists(EXTRACT_PDF):
        os.unlink(EXTRACT_PDF)
    try:
        latex_tools.extract_pdf_pages(EXTRACT_PDF,FIVEPAGES_PDF,pagelist=[1])
    except latex_tools.LatexException as e:
        warnings.warn("LatexException: "+str(e))
        return

    assert os.path.exists(EXTRACT_PDF)
    assert os.path.exists(FIVEPAGES_PDF)

    # Make sure precisely one page was extracted
    count = latex_tools.count_pdf_pages(EXTRACT_PDF)
    if count!=1:
        raise RuntimeError("{} does not have {} pages; it has {}".format(
            EXTRACT_PDF,1,count))

    # Finally, delete the extracted file
    os.unlink(EXTRACT_PDF)

LINE1=r'\newlabel{"1 Cover Sheet"}{{1}{6}{2017 Food File}{chapter.1}{}}'
LINE2=r'\newlabel{EOF-"1 Cover Sheet"}{{1}{99}{2017 Food File}{chapter.1}{}}'
LINE1_PARSED=[(0, '"1 Cover Sheet"'), (1, '1'), (1, '6'), (1, '2017 Food File'), (1, 'chapter.1'), (1, ''), (0, '{1}{6}{2017 Food File}{chapter.1}{}')]


if __name__=="__main__":
    parse_nested_braces_test()
    test_inspect_pdf()
    test_count_pdf_pages_pypdf()
    #print(data)
