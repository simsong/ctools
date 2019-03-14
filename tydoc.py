#!/usr/bin/env python3
"""
tydoc.py:

Module for typesetting documents in ASCII, LaTeX, and HTML.  Perhaps even CSV!

Simson Garfinkel, 2019-

This python is getting better, but still, please let me clean it up before you copy it.
tydoc is the main typesetting class. It builds an abstract representation of a document 
in memory then typesets with output in Text, HTML or LateX. 
It can do fancy things like create headers and paragraphs. 

We may rewrite this to do everything with XML internally. 
"""

#if __name__ == "__main__" or __package__=="":
#    __package__ = "ctools"

from latex_tools import latex_escape
__version__ = "0.0.1"

class elem:
    """Abstract element."""
    pass

class p(elem):
    pass

class tydoc:
    """Python class for representing arbitrary documents. Can render into ASCII, HTML and LaTeX"""
    def __init__(self, mode=None):
        self.clear()
        self.options = set()

    def clear(self):
        self.doc     = []

    def p(self, text):
        """Add a paragraph"""
        
        
def render(doc,depth=0):
    print('[{}]'.format(doc.tag),end='')
    if doc.text!=None:
        print(doc.text,end='')
    for child in doc:
        render(child,depth=depth+1)
        if child.tail!=None:
            print(child.tail,end='')
    print('[/{}]'.format(doc.tag),end='')




if __name__=="__main__":
    import xml.etree.ElementTree as ET
    tree = ET.parse('test.xml')
    root = tree.getroot()
    print(root)
    print(ET.tostring(root,encoding='unicode'))
    render(root)
