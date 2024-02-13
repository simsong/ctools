#!/usr/bin/env python

from ctools.tydoc import tytable
import sys
import os
import os.path
import warnings

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))


def test_tydoc_np():
    try:
        import numpy
    except ImportError:
        warnings.warn("Cannot test numpy")
        return
    data = numpy.array([1, 2, 3, 4, 5])
    doc = tytable()
    doc.add_head(["one", 'two', 'three', 'four', 'five'])
    doc.add_data(data)
    doc.render(sys.stdout, 'html')


if __name__ == "__main__":
    test_tydoc_np()
