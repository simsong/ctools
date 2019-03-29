#!/usr/bin/env python3
"""
tydoc.py:

Module for typesetting documents in ASCII, LaTeX, and HTML.  Perhaps even CSV!

Simson Garfinkel, 2019-

This python is getting better, but still, please let me clean it up before you copy it.
Documents are stored internally as a python XML Element Tree, with these modifications:

- For many tags, we use a subclass of xml.etree.ElementTree that adds more methods.
- Some metdata that's important for LaTeX is stored as attributes in the nodes.
- Although you *can* use ET.tostring() to generate HTML, this module has a set of rendering
  classes that can save as HTML, MarkDown or LaTeX, and that make prettier HTML.

Special classes to consider:

TyTag - subclass of xml.etree.ElementTree, supports an options
        framework that includes round-tripping into HTML. Options are text
        tags that can be added or removed to control how something formats or
        is typeset.

tydoc   - the root element. Typsets as <html>. 
          Includes methods to make it easy to construct complex text documents.
          

tytable - a class for tables. Lots of methods for adding content and formatting.

"""

__version__ = "0.1.0"

import xml.etree.ElementTree
import xml.etree.ElementTree as ET
import copy
import io
import base64
import codecs
import os
import os.path
import sys
import uuid

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
TAG_HR   = 'HR'
TAG_TABLE = 'TABLE'
TAG_CAPTION = 'CAPTION'
TAG_THEAD = 'THEAD'
TAG_TBODY = 'TBODY'
TAG_TFOOT = 'TFOOT'

ATTR_VAL = 'v'                # where we keep the original values
ATTR_TYPE = 't'              # the Python type of the value

ATTRIB_OPTIONS = 'OPTIONS'

FORMAT_HTML = 'html'
FORMAT_LATEX = 'latex'
FORMAT_TEX   = 'tex'
FORMAT_MARKDOWN = 'md'

CUSTOM_RENDERER = 'custom_renderer'
CUSTOM_WRITE_TEXT = 'custom_write_text'

# Automatically put a newline in the HTML stream after one of these tag blocks
HTML_NL_TAGS = set([TAG_P,TAG_H1,TAG_H2,TAG_H3,TAG_HTML,TAG_TABLE,TAG_PRE,TAG_TR])

LATEX_TAGS = {TAG_P:('\n','\n\n'),
              TAG_PRE:('\\begin{Verbatim}\n','\n\\end{Verbatim}\n'),
              TAG_B:('\\textbf{','}'),
              TAG_I:('\\textit{','}'),
              TAG_H1:('\\section{','}\n'),
              TAG_H2:('\\subsection{','}\n'),
              TAG_H3:('\\subsubsection{','}\n'),
              TAG_HR:('',''),   # do something better
}

MARKDOWN_TAGS = {TAG_HTML:('',''),
                 TAG_PRE:("```","```"),
                 TAG_P:('','\n\n'),
                 TAG_B:('**','**'),
                 TAG_H1:('# ','\n'),
                 TAG_H2:('## ','\n'),
                 TAG_H3:('### ','\n'),
                 TAG_HR:('='*64,'\n')
                 }

# For the Python
OPTION_LONGTABLE = 'longtable' # use LaTeX {longtable} environment
OPTION_TABLE     = 'table'    # use LaTeX {table} enviornment
OPTION_TABULARX  = 'tabularx' # use LaTeX {tabularx} environment
OPTION_CENTER    = 'center'   # use LaTeX {center} environment
OPTION_NO_ESCAPE = 'noescape' # do not escape LaTeX values
OPTION_SUPPRESS_ZERO    = "suppress_zero" # suppress zeros
LATEX_COLSPEC    = 'latex_colspec'

ATTRIB_TEXT_FORMAT = 'TEXT_FORMAT'
ATTRIB_NUMBER_FORMAT = 'NUMBER_FORMAT'
ATTRIB_INTEGER_FORMAT = 'INTEGER_FORMAT'
ATTRIB_FONT_SIZE   = 'FONTSIZE'
ATTRIB_TITLE       = 'TITLE'
ATTRIB_FOOTER      = 'FOOTER'
ATTRIB_LABEL       = 'LABEL'

ALIGN_LEFT   = "LEFT"
ALIGN_CENTER = "CENTER"
ALIGN_RIGHT  = "RIGHT"

DEFAULT_ALIGNMENT_NUMBER = ALIGN_RIGHT
DEFAULT_ALIGNMENT_STRING = ALIGN_LEFT

DEFAULT_TEXT_FORMAT = '{}'
DEFAULT_NUMBER_FORMAT = '{:,}'
DEFAULT_INTEGER_FORMAT = '{:,}'

def render(doc, f, format=FORMAT_HTML):
    """Custom rendering tool. Use the built-in rendering unless the
    Element has its own render method. Write results to f, which can
    be a file or an iobuffer"""

    if hasattr(doc,CUSTOM_RENDERER):
        return doc.custom_renderer(f, format=format)

    tbegin = doc.tbegin(format=format) if hasattr(doc,"tbegin") else None
    tend   = doc.tend(format=format)   if hasattr(doc,"tend") else None

    if tbegin is None:
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
        if hasattr(doc,CUSTOM_WRITE_TEXT):
            doc.custom_text(f, format=format)
        else:
            f.write( doc.text )
    for child in doc:
        render(child, f, format=format)
        if child.tail!=None:
            f.write(child.tail)
    f.write(tend)
    if doc.tag.upper() in HTML_NL_TAGS:
        f.write("\n")


################################################################
# some formatting codes
#
def safenum(v):
    """Return v as an int if possible, then as a float, otherwise return it as is"""
    try:
        return int(v)
    except (ValueError, TypeError):
        pass
    try:
        return float(v)
    except (ValueError, TypeError):
        pass
    return v


def scalenum(v, minscale=0):
    """Like safenum, but automatically add K, M, G, or T as appropriate"""
    v = safenum(v)
    if type(v) == int:
        for (div, suffix) in [[1_000_000_000_000, 'T'], [1_000_000_000, 'G'], [1_000_000, 'M'], [1_000, 'K']]:
            if (v > div) and (v > minscale):
                return str(v // div) + suffix
    return v


################################################################

class TyTag(xml.etree.ElementTree.Element):
    def prettyprint(self):
        s = ET.tostring(doc,encoding='unicode')
        return xml.dom.minidom.parseString( s ).toprettyxml(indent='  ')
    
    def render(self,f, format='html'):
        return render(self, f, format=format)
    
    def write_text(self,f, format='html'):
        if format==FORMAT_LATEX:
            if option( OPTION_NO_ESCAPE) :
                f.write( self.text )
            else:
                f.write( latex_escape( self.text ))
        else:
            f.write( self.text )

    def options_as_set(self):
        """Return all of the options as a set"""
        try:
            return set(self.attrib[ATTRIB_OPTIONS].split(','))
        except KeyError as e:
            return set()

    def set_option(self, option):
        """@param option is a string that is added to the 'option' attrib. They are separated by commas"""
        options = self.options_as_set()
        options.add(option)
        self.attrib[ATTRIB_OPTIONS] = ','.join(options)

    def clear_option(self, option):
        """@param option is a string that is added to the 'option' attrib. They are separated by commas"""
        options = self.options_as_set()
        options.remove(option)
        self.attrib[ATTRIB_OPTIONS] = ','.join(options)

    def option(self, option):
        """Return true if option is set."""
        return option in self.options_as_set()

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
        elif format==FORMAT_MARKDOWN:
            raise RuntimeError("markdown embedded images not supported yet")
        else:
            raise RuntimeError("unknown format: {}".format(format))
        
class tydoc(TyTag):
    """Python class for representing arbitrary documents. Can render into
    ASCII, HTML and LaTeX"""

    # We have a custom begin and end text for latex

    def __init__(self, format=None):
        super().__init__(TAG_HTML)
        self.options = set()

    def latex_package_list(self):
        packages=['graphicx','tabularx','longtable']
        return "".join([('\\usepackage{%s}\n' % package) for package in packages])


    def tbegin(self, format=None):
        """Provide custom tags for Latex"""
        if format==FORMAT_LATEX:
            return ("\\documentclass{article}\n" +
                    self.latex_package_list() +
                    "\\begin{document}\n")
        return None

    def tend(self, format=None):
        if format==FORMAT_LATEX:
            return "\\end{document}\n"
        return None

    def save(self,f_or_fname,format=None,**kwargs):
        """Save to a filename or a file-like object"""
        if not format:
            format = os.path.splitext(f_or_fname)[1].lower()
            if format[0:1]=='.':
                format=format[1:]

        if isinstance(f_or_fname, io.IOBase):
            self.render(f_or_fname, format=format)
            return

        with open(f_or_fname,"w") as f:
            self.render(f, format=format)
            return

    def add(self, tag, *args):
        """Add an element with type 'tag' for each item in args.  If args has
        elements inside it, add them as subelements, with text set to
        the tail."""

        e       = TyTag(tag)
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

    def hr(self):
        """Add a horizontal rule"""
        self.add(TAG_HR)
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
    ttable() class, which was a hack that evolved. This class has a
    similar API, but it is a complete rewrite. Most of the old API is 
    preserved, but it's not identical, so the original ttable is available 
    in the tytable.ttable() module. We apologize for the name confusion between
    tytable.ttable() (the ttable class in the typeset-table module) and the 
    tydoc.tytable() class (the typeset table class in the typset document module.)

    Note:

    1. Format for table cells must be specified in advance, and formatting is done
       when data is put into the table.  If format is changed, table
       is reformatted.

    2. Orignal numeric data and type are kept as HTML attribs.

    3. Creating a <table> HTML tag automatically creates child <thead>, <tbody> and <tfoot> nodes.
       Most people don't know that these tags even exist, but the browsers do.
    """

    VALID_ALIGNS = set([ALIGN_LEFT,ALIGN_CENTER,ALIGN_RIGHT])


    @staticmethod
    def cells_in_row(tr):
        return list( filter(lambda t:t.tag in (TAG_TH, TAG_TD), tr) )

    def __init__(self):
        super().__init__('table')
        
        self.options = set()
        self.attrib[ATTRIB_TEXT_FORMAT]   = DEFAULT_TEXT_FORMAT
        self.attrib[ATTRIB_NUMBER_FORMAT] = DEFAULT_NUMBER_FORMAT
        self.attrib[ATTRIB_INTEGER_FORMAT] = DEFAULT_INTEGER_FORMAT
        # Create the layout of the generic table
        self.add(TAG_CAPTION)
        self.add(TAG_THEAD)
        self.add(TAG_TBODY)
        self.add(TAG_TFOOT)
    
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
        self.render_latex_table_head(f)
        f.write("\\hline\n")
        self.render_latex_table_body(f)
        f.write("\\hline\n")
        self.render_latex_table_foot(f)

    def latex_cell_text(self,cell):
        if self.option(OPTION_NO_ESCAPE):
            return cell.text
        else:
            return latex_escape(cell.text)

    def render_latex_table_row(self,f,tr):
        """Render the first set of rows that were added with the add_head() command"""
        f.write(' & '.join([self.latex_cell_text(cell) for cell in tr]))
        f.write('\\\\\n')
        
    def render_latex_table_head(self,f):
        myid = uuid.uuid4().hex
        if self.option(OPTION_TABLE) and self.option(OPTION_LONGTABLE):
            raise RuntimeError("options TABLE and LONGTABLE conflict")
        if self.option(OPTION_TABULARX) and self.option(OPTION_LONGTABLE):
            raise RuntimeError("options TABULARX and LONGTABLE conflict")
        if self.option(OPTION_TABLE):
            # LaTeX table - a kind of float
            f.write('\\begin{table}\n')
            caption = self.caption()
            if caption is not None:
                f.write("\\caption{%s}" % caption)
            try:
                f.write(r"\label{%s}" % myid) # always put in myid
                f.write(r"\label{%s}" % self.attrib[ATTRIB_LABEL]) # put in label if provided
            except KeyError:
                pass            # no caption
            f.write("\n")
            if self.option(OPTION_CENTER):
                f.write('\\begin{center}\n')
        if self.option(OPTION_LONGTABLE):
            f.write('\\begin{longtable}{%s}\n' % self.latex_colspec())
            caption = self.caption()
            if caption is not None:
                f.write("\\caption{%s}\n" % caption)
            try:
                f.write("\\label{%s}" % myid) # always output myid
                f.write("\\label{%s}" % self.attrib[ATTRIB_LABEL])
            except KeyError:
                pass            # no caption
            f.write("\n")
            for tr in self.findall("./THEAD/TR"):
                self.render_latex_table_row(f,tr)
            f.write('\\hline\\endfirsthead\n')
            f.write('\\multicolumn{%d}{c}{(Table \\ref{%s} continued)}\\\\\n' % (self.max_cols(), myid))
            f.write('\\hline\\endhead\n')
            f.write('\\multicolumn{%d}{c}{(continued on next page)}\\\\\n' % (self.max_cols()))
            f.write('\\hline\\endfoot\n')
            f.write('\\hline\\hline\n\\endlastfoot\n')
        else:
            # Not longtable, so regular table
            if self.option(OPTION_TABULARX):
                f.write('\\begin{tabularx}{\\textwidth}{%s}\n' % self.latex_colspec())
            else:
                f.write('\\begin{tabular}{%s}\n' % self.latex_colspec())
            for tr in self.findall("./THEAD/TR"):
                self.render_latex_table_row(f,tr)
            
    def render_latex_table_body(self,f):
        """Render the rows that were not added with add_head() command"""
        for tr in self.findall("./TBODY/TR"):
            self.render_latex_table_row(f,tr)

    def render_latex_table_foot(self,f):
        for tr in self.findall("./TFOOT/TR"):
            self.render_latex_table_row(f,tr)
        if self.option(OPTION_LONGTABLE):
            f.write('\\end{longtable}\n')
        else:
            if self.option(OPTION_TABULARX):
                f.write('\\end{tabularx}\n')
            else:
                f.write('\\end{tabular}\n')
        if self.option(OPTION_CENTER):
            f.write('\\end{center}\n')
        if self.option(OPTION_TABLE):
            f.write('\\end{table}\n')

    def custom_renderer_md(self,f):
        for (rownumber,tr) in enumerate(self.findall(".//TR"),1):
            cols = self.cells_in_row(tr)
            f.write('|')
            f.write('|'.join([col.text for col in cols]))
            f.write('|\n')
            if rownumber==1:
                f.write('|')
                f.write('|'.join(['-'*len(col.text) for col in cols]))
                f.write('|\n')


    def set_title(self, title):
        self.attrib[ATTRIB_TITLE] = title

    def set_caption(self, caption):
        #  TODO: Validate that this is first
        """The <caption> tag must be inserted immediately after the <table> tag.
        https://www.w3schools.com/tags/tag_caption.asp
        """
        self.add(TAG_CAPTION, caption)

    def set_fontsize(self, size):
        self.attrib[ATTRIB_FONT_SIZE] = str(size)

    def set_latex_colspec(self,latex_colspec): 
        """LaTeX colspec is just used when typesetting with latex. If one is
not set, it auto-generated"""

        self.attrib[LATEX_COLSPEC] = latex_colspec

    def latex_colspec(self):
        """Use the user-supplied LATEX COLSPEC; otherwise figure one out"""
        try:
            return self.attrib[LATEX_COLSPEC]
        except KeyError as c:
            return "l"*self.max_cols()

    def add_row(self, where, cells, row_attrib={}):
        """Add a row of cells to the table.
        @param cells - a list of cells.
        """
        where_node = self.findall(f".//{where}")[0]
        row = ET.SubElement(where_node,TAG_TR, attrib=row_attrib)
        for cell in cells:
            row.append(cell)

    def format_cell(self, cell):
        """Modify cell by setting its text to be its format. Uses eval, so it's not safe."""
        try:
            typename = cell.attrib[ATTR_TYPE]
            typeval  = cell.attrib[ATTR_VAL]
        except KeyError:
            return cell

        if typename is None:
            return cell

        try:
            value = eval(typename)(typeval)
        except Exception as e:
            return cell
        try:
            if cell.attrib[ATTR_TYPE]=='int':
                cell.text = self.attrib[ATTRIB_INTEGER_FORMAT].format(int(value))
            else:
                cell.text = self.attrib[ATTRIB_NUMBER_FORMAT].format(float(value))
        except ValueError as e:
            cell.text = self.attrib[ATTRIB_TEXT_FORMAT].format(value)
        return cell

    def make_cell(self, tag, value, attrib):
        """Given a tag, value and attributes, return a cell formatted with the default format"""
        cell = ET.Element(tag,{**attrib,
                                 ATTR_VAL:str(value),
                                 ATTR_TYPE:str(type(value).__name__)
                                 })
        self.format_cell(cell)
        return cell


    def add_row_values(self, where, tags, values, cell_attribs={}, *, row_attrib={}):
        """Create a row of cells and add it to the table.
        @param tags - a list of tags
        @param values - a list of values.  Each is automatically formatted.
        """
        # If tags is not a list, make it a list
        if not isinstance(tags,list):
            tags = [tags] * len(values)

        if not isinstance(cell_attribs,list):
            cell_attribs = [cell_attribs] *len(values)

        assert len(tags)==len(values)==len(cell_attribs)
        cells = [self.make_cell(t,v,a) for (t,v,a) in zip(tags,values,cell_attribs)]
        self.add_row(where, cells, row_attrib=row_attrib)
        
    def add_head(self, values, row_attrib={}):
        self.add_row_values(TAG_THEAD, 'TH',values)

    def add_data(self, values, row_attrib={}):
        self.add_row_values(TAG_TBODY, 'TD',values)

    def add_foot(self, values, row_attrib={}):
        self.add_row_values(TAG_TFOOT, 'TD',values)

    def add_data_array(self, rows):
        for row in rows:
            self.add_data(row)

    def caption(self):
        """Return the <caption> tag text"""
        try:
            c = self.findall(".//CAPTION")
            return c[0].text
        except (KeyError,IndexError) as e:
            return None

    def rows(self):
        """Return the rows"""
        return self.findall(".//TR")

    def row(self,n):
        """Return the nth row; n starts at 0"""
        return self.rows()[n]

    def max_cols(self):
        """Return the number of maximum number of cols in the data"""
        return max( len(row.findall("*")) for row in self.rows())
        
    def get_cell(self, row, col):
        """Return the cell at row, col; both start at 0"""
        return self.cells_in_row( self.row(row) ) [col]
        
    def col(self,n):
        """Returns all the cells in column n"""
        return [row[n] for row in self.rows()]

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
    d2.set_option(OPTION_TABLE)
    d2.add_head(['State','Abbreviation','Rank','Population','% Change'])
    d2.add_data(['California','CA',1,37252895,10.0])
    d2.add_data(['Virginia','VA',12,8001045,13.0])

    doc.p("")

    d2 = doc.table()
    d2.set_option(OPTION_LONGTABLE)
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

