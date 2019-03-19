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

import xml.etree.ElementTree
import xml.etree.ElementTree as ET
import copy
import io
import base64
import codecs
import os
import os.path
import sys

sys.path.append( os.path.dirname(__file__))
from latex_tools import latex_escape

TAG_P    = 'P'
TAG_B    = 'B'
TAG_I    = 'I'
TAG_H1   = 'H1'
TAG_H2   = 'H2'
TAG_H3   = 'H3'
TAG_HTML = 'HTML'
TAG_PRE  = 'PRE'
TAG_TR   = 'TR'
TAG_TH   = 'TH'
TAG_TD   = 'TD'

ATTR_VAL = 'v'                # where we keep the original values
ATTR_TYPE = 't'              # the Python type of the value

LATEX_PREAMBLE="""
\\documentclass{article}
\\usepackage{graphicx}
\\begin{document}
"""

LATEX_TRAILER="""
\\end{document}
"""

FORMAT_HTML = 'html'
FORMAT_LATEX = 'latex'
FORMAT_TEX   = 'tex'
FORMAT_MARKDOWN = 'md'

CUSTOM_RENDERER = 'custom_renderer'

LATEX_TAGS = {TAG_HTML:(LATEX_PREAMBLE,LATEX_TRAILER),
              TAG_P:('\n','\n\n'),
              TAG_B:(r'\textbf{','}'),
              TAG_I:(r'\textit{','}'),
              TAG_H1:(r'\section{','}'),
              TAG_H2:(r'\subsection{','}'),
              TAG_H3:(r'\subsubsection{','}') }

MARKDOWN_TAGS = {TAG_HTML:('',''),
                 TAG_P:('','\n\n'),
                 TAG_B:('**','**'),
                 TAG_H1:('# ','\n'),
                 TAG_H2:('## ','\n'),
                 TAG_H3:('### ','\n')}

def render(f, doc, format=FORMAT_HTML):
    """Custom rendering tool. Use the built-in rendering unless the
    Element has its own render method. Write results to f, which can
    be a file or an iobuffer"""

    if hasattr(doc,CUSTOM_RENDERER):
        return doc.custom_renderer(f, format=format)

    if format==FORMAT_HTML:
        tbegin = f'<{doc.tag}>'
        tend   = f'</{doc.tag}>'
    elif format==FORMAT_LATEX or format==FORMAT_TEX:
        (tbegin,tend) = LATEX_TAGS[doc.tag.upper()]
    elif format==FORMAT_MARKDOWN:
        (tbegin,tend) = MARKDOWN_TAGS[doc.tag.upper()]
    else:
        raise RuntimeError("unknown format: {}".format(format))

    f.write(tbegin)
    if doc.text!=None:
        f.write(doc.text)
    for child in doc:
        render(f, child, format=format)
        if child.tail!=None:
            f.write(child.tail)
    f.write(tend)


class TyTag(xml.etree.ElementTree.Element):
    def prettyprint(self):
        s = ET.tostring(doc,encoding='unicode')
        return xml.dom.minidom.parseString( s ).toprettyxml(indent='  ')
    
    def render(self,f, format='html'):
        return render(f, self, format=format)
    
    def options_as_set(self):
        """Return all of the options as a set"""
        try:
            return set(self.attrib['OPTIONS'].split(','))
        except KeyError as e:
            return set()

    def set_option(self, option):
        """@param option is a string that is added to the 'option' attrib. They are separated by commas"""
        options = self.options_as_set()
        options.add(option)
        self.attrib['OPTIONS'] = ','.join(options)

    def clear_option(self, option):
        """@param option is a string that is added to the 'option' attrib. They are separated by commas"""
        options = self.options_as_set()
        options.remove(option)
        self.attrib['OPTIONS'] = ','.join(options)

    def option(self, option):
        """Return true if option is set."""
        return option in self.options_as_set()

class EmbeddedImageTag(TyTag):
    def __init__(self, buf, *, format, alt=""):
        """Create an image. You must specify the format. 
        buf can be a string of a BytesIO"""
        super().__init__('img')
        self.buf    = buf
        self.alt    = alt
        self.format = format

    def custom_renderer(self, f, alt="", format=FORMAT_HTML):
        if format==FORMAT_HTML:
            f.write('<img alt="{}" src="data:image/{};base64,{}" />'.format(
                self.alt,self.format,codecs.decode(base64.b64encode(self.buf))))
        elif format in (FORMAT_LATEX, FORMAT_TEX):
            fname = os.path.splitext(f.name)[0]+"_image.png"
            with open(fname,"wb") as f2:
                f2.write(self.buf)
            f.write(f'\\includegraphics{fname}\n')
        raise RuntimeError("unknown format: {}".format(format))
        

class tydoc(TyTag):
    """Python class for representing arbitrary documents. Can render into
    ASCII, HTML and LaTeX"""
    def __init__(self, format=None):
        super().__init__('html')
        self.options = set()

    def save(self,fout,format=None,**kwargs):
        """Save to a filename or a file-like object"""
        if not format:
            format = os.path.splitext(fout)[1].lower()
            if format[0:1]=='.':
                format=format[1:]

        if isinstance(fout, io.IOBase):
            self.render(fout, format=format)
            return

        with open(fout,"w") as outfile:
            self.render(fout, format=format)
            return

    def add(self, tag, *args):
        """Add an element with type 'tag' for each item in args.  If args has
        elements inside it, add them as subelements, with text set to
        the tail."""

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

    def insert_image(self, buf, *, format):
        if isinstance(buf,io.BytesIO):
            buf.seek(0)
            buf = buf.read()    # turn it into a buffer
        img = EmbeddedImageTag(buf,format=format)
        self.append(img)

    def insert_matplotlib(self, plt, *, format="png", **kwargs):
        buf = io.BytesIO()
        plt.savefig(buf, format=format, **kwargs)
        buf.seek(0)
        self.insert_image(buf,format='png')

    def p(self, *text):
        """Add a paragraph. Multiple arguments are combined and can be text or other HTML elements"""
        self.add(TAG_P, *text)
        return self
        
    def h1(self, *text):
        """Add a H1"""
        self.add(TAG_H1, *text)
        return self

    def h2(self, *text):
        """Add a H2"""
        self.add(TAG_H2, *text)
        return self

    def h3(self, *text):
        """Add a H3"""
        self.add(TAG_H3, *text)
        return self

    def pre(self, *text):
        """Add a preformatted"""
        self.add(TAG_PRE, *text)
        return self

    def table(self, **kwargs):
        t = tytable()
        self.append(t)
        return t

################################################################
### Improved tytable with the new API.
### Class name has changed from ttable to tytable.
### It now uses the XML ETree to represent the table.
### Tables can then be rendered into HTML or another form.
################################################################
class tytable(TyTag):
    """Python class for representing a table that can be rendered into
    HTML or LaTeX or text.  Based on Simson Garfinkel's legacy
    ttable() class, which was hack that evolved. This class has a
    similar API, but it's not identical, so the old class appears
    below.

    Key differences:

    1. Format must be specified in advance, and formatting is done
       when data is put into the table.  If format is changed, table
       is reformatted.

    2. Orignal numeric data is kept as num= option
    """

    # For the Python
    OPTION_LONGTABLE = 'longtable' # use LaTeX {longtable} environment
    OPTION_TABLE     = 'table'  # use LaTeX {table} enviornment
    OPTION_TABULARX  = 'tabularx' # use LaTeX {tabularx} environment
    OPTION_CENTER    = 'center'   # use LaTeX {center} environment
    OPTION_NO_ESCAPE = 'noescape' # do not escape values
    OPTION_SUPPRESS_ZERO    = "suppress_zero" # suppress zeros
    VALID_OPTIONS = set([OPTION_LONGTABLE,OPTION_TABULARX,OPTION_SUPPRESS_ZERO,OPTION_TABLE])
    TEXT  = 'text'
    LATEX = 'latex'
    HTML  = 'html'
    MARKDOWN = 'markdown'
    VALID_MODES = set([TEXT,LATEX,HTML,MARKDOWN])
    LATEX_COLSPEC = 'latex_colspec'

    ALIGN_LEFT="LEFT"
    ALIGN_CENTER="CENTER"
    ALIGN_RIGHT="RIGHT"
    VALID_ALIGNS = set([ALIGN_LEFT,ALIGN_CENTER,ALIGN_RIGHT])

    DEFAULT_ALIGNMENT_NUMBER = ALIGN_RIGHT
    DEFAULT_ALIGNMENT_STRING = ALIGN_LEFT

    def __init__(self):
        super().__init__('table')
        self.options = set()
        self.clear()
        self.text_format = "{}"
        self.number_format = "{:,}"
    
    def custom_renderer(self, f, alt="", format=FORMAT_HTML):
        if format in (FORMAT_HTML):
            f.write(ET.tostring(self,encoding='unicode'))
        elif format in (FORMAT_LATEX,FORMAT_TEX):
            self.custom_renderer_latex(f)
        elif format in (FORMAT_MARKDOWN):
            self.custom_renderer_md(f)
        else:
            RuntimeError("unknown format: {}".format(format))
        
    def custom_renderer_latex(self,f):
        self.render_latex_table_header(f)
        self.render_latex_table_body(f)
        self.render_latex_table_footer(f)

    def render_latex_table_header(self,f):
        pass

    def render_latex_table_body(self,f):
        pass

    def render_latex_table_footer(self,f):
        pass

    def custom_renderer_md(self,f):
        for (rownumber,tr) in enumerate(self.findall(".//TR"),1):
            cols = list(filter(lambda t:t.tag in (TAG_TH,TAG_TD), tr))
            f.write('|')
            f.write('|'.join([col.text for col in cols]))
            f.write('|\n')
            if rownumber==1:
                f.write('|')
                f.write('|'.join(['-'*len(col.text) for col in cols]))
                f.write('|\n')


    def set_latex_colspec(self,latex_colspec): 
        """LaTeX colspec is just used when typesetting with latex. If one is not set, it auto-generated"""
        self.attrib[LATEX_COLSPEC] = latex_colspec

    def latex_colspec(self):
        """Figure out latex colspec"""
        return self.attrib[LATEX_COLSPEC]

    def add_row(self, cells):
        """Add a row of cells to the table.
        @param cells - a list of cells.
        """
        row = ET.SubElement(self,TAG_TR)
        for cell in cells:
            row.append(cell)

    def make_cell(self, tag, value, attrs):
        cell = ET.Element(tag,{**attrs,
                                 ATTR_VAL:str(value),
                                 ATTR_TYPE:str(type(value).__name__)
                                 })
        cell.text = str(value)
        return cell

    def add_row_values(self, tags, values, attrs={}):
        """Create a row of cells and add it to the table.
        @param tags - a list of tags
        @param values - a list of values.  Each is automatically formatted.
        """
        # If tags is not a list, make it a list
        if not isinstance(tags,list):
            tags = [tags] * len(values)

        if not isinstance(attrs,list):
            attrs = [attrs] *len(values)

        assert len(tags)==len(values)==len(attrs)
        cells = [self.make_cell(t,v,a) for (t,v,a) in zip(tags,values,attrs)]
        self.add_row(cells)
        
    def add_head(self, values):
        self.add_row_values('TH',values)

    def add_data(self, values):
        self.add_row_values('TD',values)

    def rows(self):
        """Return the rows"""
        return self.findall(".//TR")

    def max_cols(self):
        """Return the number of maximum number of cols in the data"""
        return max( len(row.findall("*")) for row in self.rows())
        
        
################################################################
##
## covers for making it easy to construct HTML
##
################################################################

# Add some covers for popular paragraph types
def p(*text):
    """Return a paragraph. Text runs are combined"""
    return tydoc().p(*text)

def h1(*text):
    """Return a header 1"""
    return tydoc().h1(*text)

def h2(*text):
    """Return a header 2"""
    return tydoc().h2(*text)

def h3(*text):
    """Return a header 3"""
    return tydoc().h3(*text)

def pre(*text):
    """Return preformatted text"""
    return tydoc().pre(*text)

def b(text):
    """Return a bold run"""
    e = ET.Element('b')
    e.text=text
    return e

def i(text):
    """Return an itallic run """
    e = ET.Element('i')
    e.text=text
    return e

def showcase(doc):
    print("----------")
    print(ET.tostring(doc,encoding='unicode'))
    print("\n----------")
    doc.render(sys.stdout, format='html')
    print("\n----------")
    doc.render(sys.stdout, format='latex')
    print("\n----------")
    doc.render(sys.stdout, format='md')
    print("\n==========")

def demo1():
    # Verify that render works
    doc  = ET.fromstring("<html><p>First Paragraph</p><p>Second <b>bold</b> Paragraph</p></html>")
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

def tabdemo1():
    doc = tydoc()
    doc.h1("Table demo")
    d2 = doc.table()
    d2.add_head(['State','Abbreviation','Population'])
    d2.add_data(['Virginia','VA',8001045])
    d2.add_data(['California','CA',37252895])
    return doc

if __name__=="__main__":
    # Showcase different ways of making a document and render it each
    # way:
    if False:
        showcase(demo1())
        showcase(demo2())
        showcase(demo3())
        showcase(demo4())
    showcase(tabdemo1())
    exit(0)

