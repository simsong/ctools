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

__version__ = "0.0.1"

import xml.etree.ElementTree as ET
from latex_tools import latex_escape
from tytable import ttable
import copy

def render(doc,depth=0):
    print('<{}>'.format(doc.tag),end='')
    if doc.text!=None:
        print(doc.text,end='')
    for child in doc:
        render(child,depth=depth+1)
        if child.tail!=None:
            print(child.tail,end='')
    print('</{}>'.format(doc.tag),end='')

TAG_P = 'p'
TAG_H1 = 'h1'
TAG_H2 = 'h2'
TAG_H3 = 'h3'
TAG_B  = 'b'
TAG_I  = 'i'

import xml.etree.ElementTree
class tydoc(xml.etree.ElementTree.Element):
    """Python class for representing arbitrary documents. Can render into
    ASCII, HTML and LaTeX"""
    TEXT=ttable.TEXT
    def __init__(self, mode=None):
        super().__init__('tydoc')
        self.options = set()

    def add(self, tag, *args):
        """Add an element with type 'tag' for each item in args.
        If args has elements inside it, add them as subelements, with text set to the tail."""

        e       = ET.SubElement(self, tag)
        lastTag = None
        for arg in args:
            if not isinstance(arg, ET.Element):
                if lastTag is not None:
                    if lastTag.tail == None:
                        lastTag.tail = ""
                    lastTag.tail  += str(arg)
                else:
                    if e.text == None:
                        e.text = ""
                    e.text += str(arg)
            else:
                # Copy the tag into place
                lastTag = copy.deepcopy(arg)
                e.append(lastTag)
        return self

    def p(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_P, *text)
        return self
        
    def b(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_B, *text)
        return self

    def typeset(self, mode=None):
        render(self)
        return self

# Add some covers for popular paragraph types
def p(*text):
    """Return a pydoc with one or more paragraphs"""
    return tydoc().p(*text)

def b(text):
    """Return a pydoc with one or more bold runs"""
    e = ET.Element('b')
    e.text=text
    return e

def i(*text):
    """Return a pydoc with one or more bold runs"""
    return tydoc().b(*text)

def h1(*text):
    """Return a pydoc with one or more bold runs"""
    return tydoc().h1(*text)

def h2(*text):
    """Return a pydoc with one or more bold runs"""
    return tydoc().h2(*text)

def h3(*text):
    """Return a pydoc with one or more bold runs"""
    return tydoc().h3(*text)

def showcase(doc):
    print(ET.tostring(doc,encoding='unicode'))
    render(doc)
    print()
    print("----------")

def demo1():
    # Verify that render works
    doc  = ET.fromstring("<tydoc><p>First Paragraph</p><p>Second <b>bold</b> Paragraph</p></tydoc>")
    print("doc=",doc)
    return doc

def demo2():
    doc = ET.Element("tydoc")
    ET.SubElement(doc, 'p').text = "First Paragraph"

    p = ET.SubElement(doc, 'p')
    p.text = "Second "

    b = ET.SubElement(p, 'b')
    b.text = "bold"
    b.tail = " Paragraph"
    return doc

def demo3():
    b = ET.Element('b')
    b.text = "bold"

    doc = tydoc()
    doc.p("First Paragraph")
    doc.p("Second ",b, " Paragraph")
    return doc

def demo4():
    doc = tydoc()
    doc.p("First Paragraph")
    doc.p("Second ",b('bold'), " Paragraph")
    return doc

    

if __name__=="__main__":
    showcase(demo1())
    showcase(demo2())
    showcase(demo3())
    showcase(demo4())
    exit(0)

