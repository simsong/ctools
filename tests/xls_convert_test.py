import py.test
import os
import sys
import warnings

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
print(sys.path)
from ctools.xls_convert import excel_convert

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")
TEST_XLSX=os.path.join(TEST_FILES_DIR,"test-input-excel_convert.xlsx")
TEST_PDF=TEST_XLSX.replace("xlsx","pdf")

# Count the number of pages in a PDF using pure python this works for
# PDF 1.5 created by Excel 2016, YMMV for other versions as it is untested
# https://www.daniweb.com/programming/software-development/threads/152831/read-number-of-pages-in-pdf-files

import re
def countPages(filename):
    with open(filename, "rb", 1) as pfile:
        for pline in pfile.readlines():
            if "/Count " in str(pline):
                pages = int(re.search(r"/Count \d*", str(pline)).group()[7:])
    return pages

def test_prep():
    if os.path.exists(TEST_PDF):
        print("Removing old test PDF at %s" % TEST_PDF)
        os.remove(TEST_PDF)
    # Ensure PDF does not exist to ensure module is tested
    assert os.path.exists(TEST_PDF) == False

def test_excel_convert():
    # Only return for excel_convert if it doesn't halt is True
    # right now, we can only do this on windows
    if sys.platform!='win32':
        warnings.warn("excel tests only run on Windows")
        return

    assert excel_convert(TEST_XLSX, ".pdf") == True
    # Verify PDF was created
    assert os.path.exists(TEST_PDF) == True
    # Each sheet outputs to 2 pages so total should be 4
    assert countPages(TEST_PDF) == 4
