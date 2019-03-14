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

TAG_P = 'p'
TAG_B  = 'b'
TAG_I  = 'i'
TAG_H1 = 'h1'
TAG_H2 = 'h2'
TAG_H3 = 'h3'
TAG_HTML = 'html'

LATEX_TAGS = {TAG_HTML:r'',
              TAG_P:'\n\n',
              TAG_B:r'\textbf',
              TAG_I:r'\textit',
              TAG_H1:r'\section',
              TAG_H2:r'\subsection',
              TAG_H3:r'\subsubsection'}

MARKDOWN_TAGS = {TAG_HTML:('',''),
                 TAG_P:('','\n\n'),
                 TAG_B:('**','**'),
                 TAG_H1:('# ',''),
                 TAG_H2:('## ',''),
                 TAG_H3:('### ','')}

def render(doc,mode=ttable.HTML):
    if mode==ttable.HTML:
        tbegin = f'<{doc.tag}>'
        tend   = f'</{doc.tag}>'
    elif mode==ttable.LATEX:
        tbegin = LATEX_TAGS[doc.tag] + '{'
        tend   = '}'
    elif mode==ttable.MARKDOWN:
        (tbegin,tend) = MARKDOWN_TAGS[doc.tag]

    ret = []
    ret.append(tbegin)
    if doc.text!=None:
        ret.append(doc.text)
    for child in doc:
        ret.append( render(child,mode=mode) )
        if child.tail!=None:
            ret.append(child.tail)
    ret.append(tend)

    # Now do a flatten
    flatten = [item for sublist in ret for item in sublist]

    return "".join(flatten)

import xml.etree.ElementTree
class tydoc(xml.etree.ElementTree.Element):
    """Python class for representing arbitrary documents. Can render into
    ASCII, HTML and LaTeX"""
    def __init__(self, mode=None):
        super().__init__('html')
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

    def i(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_I, *text)
        return self

    def h1(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_H1, *text)
        return self

    def h2(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_H2, *text)
        return self

    def h3(self, *text):
        """Add one or more paragraph"""
        self.add(TAG_H3, *text)
        return self

    def typeset(self, mode=None):
        return render(self)

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
    print(render(doc))
    print(render(doc,mode=ttable.LATEX))
    print(render(doc,mode=ttable.MARKDOWN))
    print("----------")

def demo1():
    # Verify that render works
    doc  = ET.fromstring("<html><p>First Paragraph</p><p>Second <b>bold</b> Paragraph</p></html>")
    print("doc=",doc)
    return doc

def demo2():
    doc = ET.Element("html")
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
    # Showcase different ways of making a document and render it each way:
    showcase(demo1())
    showcase(demo2())
    showcase(demo3())
    showcase(demo4())
    exit(0)

