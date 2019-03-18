#!/usr/bin/env python3
"""
tytable.py:
Module for typesetting tables in ASCII, LaTeX, and HTML.  Perhaps even CSV!
Also creates LaTeX variables.

Simson Garfinkel, 2010-

This is really bad python. Let me clean it up before you copy it.
ttable is the main typesetting class. It builds an abstract representation of a table and then typesets with output in Text, HTML or LateX. 
It can do fancy things like add commas to numbers and total columns.
All of the formatting specifications need to be redone so that they are more flexbile
"""

import os
import os.path
import sys
import sqlite3
import xml.etree.ElementTree
import xml.etree.ElementTree as ET
import xml.dom.minidom
# not sure why this was put in, but it breaks calling tytable from this directory.
#if __name__ == "__main__" or __package__=="":
#    __package__ = "ctools"

sys.path.append( os.path.dirname(__file__))

import latex_tools 

__version__ = "0.2.1"

#
# Some basic functions for working with text and numbers
#

def isnumber(v):
    """Return true if we can treat v as a number"""
    try:
        return v == 0 or v!=0
    except TypeError:
        return False

def safeint(v):
    """Return v as an integer if it is a number, otherwise return it as is"""
    try:
        return int(v)
    except Exception:
        return v


def safefloat(v):
    """Return v as a float if it is a number, otherwise return it as is"""
    try:
        return float(v)
    except Exception:
        return v

def safenum(v):
    """Return v as an int if possible, then as a float, otherwise return it as is"""
    try:
        return int(v)
    except Exception:
        pass
    try:
        return float(v)
    except Exception:
        pass
    return v


def scalenum(v,minscale=0):
    """Like safenum, but automatically add K, M, G, or T as appropriate"""
    v = safenum(v)
    if type(v)==int:
        for (div,suffix) in [[1_000_000_000_000,'T'],
                             [1_000_000_000,    'G'],
                             [1_000_000,        'M'],
                             [1_000,            'K']]:
            if (v > div) and (v > minscale):
                return str(v//div) + suffix
    return v
            

def latex_var(name,value,desc=None,xspace=True):
    """Create a variable NAME with a given VALUE.
    Primarily for output to LaTeX.
    Returns a string."""
    xspace_str = r"\xspace" if xspace else ""
    return "".join(['\\newcommand{\\',str(name),'}{',str(value),xspace_str,'}'] + ([' % ',desc] if desc else []) + ['\n'])

def text_var(name,value,desc=None):
    """Create a variable NAME with a given VALUE.
    Primarily for output to LaTeX.
    Returns a string."""
    return "".join(['Note: ',str(name),' is ',str(value)] + ([' (',desc,')'] if desc else []))

def icomma(i):
    """ Return an integer formatted with commas """
    if i<0:   return "-" + icomma(-i)
    if i<1000:return "%d" % i
    return icomma(i/1000) + ",%03d" % (i%1000)

################################################################
### Improved tytable with the new API.
### Class name has changed from ttable to tytable.
### It now uses the XML ETree to represent the table.
### Tables can then be rendered into HTML or another form.
################################################################
class tytable(xml.etree.ElementTree.Element):
    """Python class for representing a table that can be rendered into HTML or LaTeX or text.
    Based on Simson Garfinkel's legacy ttable() class, which was hack that evolved. This class
    has a similar API, but it's not identical, so the old class appears below.

    Key differences:
    1. Format must be specified in advance, and formatting is done when data is put into the table.
       If format is changed, table is reformatted.
    2. Orignal numeric data is kept as num= option"""

    OPTION_LONGTABLE = 'longtable' # use LaTeX {longtable} environment
    OPTION_TABLE     = 'table'  # use LaTeX {table} enviornment
    OPTION_TABULARX  = 'tabularx' # use LaTeX {tabularx} environment
    OPTION_CENTER    = 'center'   # use LaTeX {center} environment
    OPTION_NO_ESCAPE = 'noescape' # do not escape values
    OPTION_SUPPRESS_ZERO    = "suppress_zero" # suppress zeros
    VALID_OPTIONS = {OPTION_LONGTABLE, OPTION_TABULARX, OPTION_SUPPRESS_ZERO, OPTION_TABLE}
    TEXT  = 'text'
    LATEX = 'latex'
    HTML  = 'html'
    MARKDOWN = 'markdown'
    VALID_MODES = {TEXT, LATEX, HTML, MARKDOWN}

    ALIGN_LEFT="LEFT"
    ALIGN_CENTER="CENTER"
    ALIGN_RIGHT="RIGHT"
    VALID_ALIGNS = {ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT}

    DEFAULT_ALIGNMENT_NUMBER = ALIGN_RIGHT
    DEFAULT_ALIGNMENT_STRING = ALIGN_LEFT

    def __init__(self, mode=None):
        super().__init__('table')
        self.set_mode(mode)
        self.options = set()
        self.clear()
    
    def prettyprint(self):
        return xml.dom.minidom.parseString( ET.tostring(doc,encoding='unicode')).toprettyxml(indent='  ')

    def set_mode(self,mode):
        assert (mode in self.VALID_MODES) or (mode is None)
        self.mode = mode

    def clear(self):
        """Clear the data and the formatting; keeps mode and options"""
        super().clear()
        self.fontsize = None
        self.latex_colspec_override = None

    def set_option(self,o):    self.options.add(o)
    def set_fontsize(self,sz): self.fontsize = sz
    def set_latex_colspec(self,latex_colspec): 
        """LaTeX colspec is just used when typesetting with latex. If one is not set, it auto-generated"""
        self.latex_colspec_override = latex_colspec

    def latex_colspec(self):
        """Figure out latex colspec"""
        pass

    def add_row(self,cellTag, cells):
        """Add a row to the table with the TR"""
        row = ET.SubElement(self,'TR')
        for cell in cells:
            e = ET.SubElement(row,cellTag,{'d':str(cell),'t':str(type(cell).__name__)})
            e.text = str(cell)
        
    def add_head(self, values):
        self.add_row('TH',values)

    def add_data(self, values):
        self.add_row('TD',values)

    def ncols(self):
        """Return the number of maximum number of cols in the data"""
        raise NotImplementedError("ncols not implemented yet")

    def nrows(self):
        """Return the number of maximum number of rows in the data"""
        raise NotImplementedError("nrows not implemented yet")

################################################################
### Legacy system follows
################################################################


# The row class holds the row and anny annotations
class Row:
    __slots__ = ['data','annotations']
    def __init__(self,data,annotations=None):
        if annotations:
            if len(data) != len(annotations):
                raise ValueError("data and annotations must have same length")
        self.data = data
        self.annotations = annotations
    def __len__(self):
        return len(self.data)
    def __getitem__(self,n):
        return self.data[n]
    def ncols(self):
        return len(self.data)

# Heads are like rows, but they are headers
class Head(Row):
    def __init__(self,data,annotations=None):
        super().__init__(data=data,annotations=annotations)

# A special class that makes a horizontal rule
class HorizontalRule(Row):
    def __init__(self):
        super().__init__(data=[])

# Raw is just raw data passed through
class Raw(Row):
    def __init__(self,rawdata):
        self.data    = rawdata
    def ncols(self):
        raise RuntimeError("Raw does not implement ncols")

def line_end(mode):
    if mode == ttable.TEXT:
        return "\n"
    elif mode == ttable.LATEX:
        return r"~\\" + "\n"
    elif mode == ttable.HTML:
        return "<br>"
    else:
        raise RuntimeError("Unknown mode: {}".format(mode))

class ttable:
    """ Python class that prints formatted tables. It can also output LaTeX.
    Typesetting:
       Each entry is formatted and then typset.
       Formatting is determined by the column formatting that is provided by the caller.
       Typesetting is determined by the typesetting engine (text, html, LaTeX, etc).
       Numbers are always right-justified, text is always left-justified, and headings
       are center-justified.

       ## Data building functions:
       ttable() - Constructor. 
       .set_title(title) 
       .compute_and_add_col_totals() - adds columns for specified columns / run automatically
       .compute_col_totals(col_totals) - adds columns for specified columns
       .add_head([row]) to one or more heading rows. 
       .add_data([row]) to append data rows. 
       .add_data(ttable.HR) - add a horizontal line

       ## Formatting functions:
       set_col_alignment(col,align) - where col=0..maxcols and align=ttable.RIGHT or ttable.LEFT or ttable.CENTER
                                (center is not implemented yet)
       set_col_alignments(str)      - sets with a LaTeX-stye format string
       set_col_totals([1,2,3,4]) - compute totals of columns 1,2,3 and 4

       ## Outputting
       typeset(mode=[TEXT,HTML,LATEX]) to typeset. returns table
       save_table(fname,mode=)
       add_variable(name,value)  -- add variables to output (for LaTeX mostly)
       set_latex_colspec(str)    -- sets the LaTeX column specification, rather than have it auto calculated
    """
    OPTION_LONGTABLE = 'longtable'
    OPTION_TABULARX = 'tabularx'
    OPTION_TABLE = 'table'
    OPTION_CENTER = 'center'
    OPTION_NO_ESCAPE = 'noescape'
    HR = HorizontalRule()
    SUPPRESS_ZERO="suppress_zero"
    TEXT_MODE = TEXT  = 'text'
    LATEX_MODE = LATEX = 'latex'
    HTML_MODE  = HTML  = 'html'
    MARKDOWN_MODE = MARKDOWN = 'markdown'
    RIGHT="RIGHT"
    LEFT="LEFT"
    CENTER="CENTER"
    NL = {TEXT:'\n', LATEX:"\\\\ \n", HTML:''} # new line
    VALID_MODES = {TEXT,LATEX,HTML}
    VALID_OPTIONS = {OPTION_LONGTABLE,OPTION_TABULARX,SUPPRESS_ZERO,OPTION_TABLE}
    DEFAULT_ALIGNMENT_NUMBER = RIGHT
    DEFAULT_ALIGNMENT_STRING = LEFT
    HTML_ALIGNMENT = {RIGHT:"style='text-align:right;'",
                      LEFT:"style='text-align:left;'",
                      CENTER:"style='text-align:center;'"}

    def __init__(self,mode=None):
        self.set_mode(mode)
        self.options      = set()
        self.clear()

    def set_mode(self,mode):
        assert (mode in self.VALID_MODES) or (mode is None)
        self.mode = mode

    def clear(self):
        """Clear the data and the formatting; keeps mode and options"""
        self.col_headings = []          # the col_headings; a list of lists
        self.data         = []          # the raw data; a list of lists
        self.omit_row     = []          # descriptions of rows that should be omitted
        self.col_widths   = []          # a list of how wide each of the formatted columns are
        self.col_margin   = 1
        self.col_fmt_default  = "{:}"   # default format gives numbers
        self.col_fmt      = {}          # format for each column
        self.title        = ""
        self.num_units    = []
        self.footer       = ""
        self.header       = None # 
        self.heading_hr_count = 1       # number of <hr> to put between heading and table body
        self.col_alignment = {}
        self.variables    = {}  # additional variables that may be added
        self.label        = None
        self.caption      = None
        self.footnote     = None
        self.autoescape    = True # default
        self.fontsize     = None


    def set_mode(self,mode):
        assert (mode in self.VALID_MODES) or (mode is None)
        self.mode = mode

    def set_fontsize(self,ft): self.fontsize = ft
    def add_option(self,o): self.options.add(o)
    def set_option(self,o): self.options.add(o)
    def set_data(self,d):   self.data = d
    def set_title(self,t):  self.title = t
    def set_label(self,l):  self.label = l
    def set_footer(self,footer): self.footer = footer
    def set_caption(self,c): self.caption = c
    def set_col_alignment(self,col,align): self.col_alignment[col] = align
    def set_col_alignmnets(self,fmt):
        col = 0
        for ch in fmt:
            if ch == 'r':
                self.set_col_alignment(col, self.RIGHT)
                col += 1
                continue
            elif ch == 'l':
                self.set_col_alignment(col, self.LEFT)
                col += 1
                continue
            else:
                raise RuntimeError("Invalid format string '{}' in '{}'".format(fmt,ch))

    def set_col_totals(self,totals): self.col_totals = totals
    def set_col_fmt(self,col,fmt):
        """Set the formatting for colum COL. Format is specified with a Python format string.
        You can create a prefix and suffix by putting them on either side of the formatter.
        e.g. prefix{:,}suffix.
        """
        self.col_fmt[col] = fmt
    def set_latex_colspec(self,latex_colspec):
        self.latex_colspec = latex_colspec

    def add_head(self,values, annotations=None):
        """ Append a row of VALUES to the table header. The VALUES should be a list of columsn."""
        assert isinstance(values,list) or isinstance(values,tuple)
        self.col_headings.append( Head(values, annotations=annotations))

    def add_subhead(self,values, annotations=None):
        self.data.append( Head(values, annotations=annotations))

    def add_data(self,values,annotations=None):
        """ Append a ROW to the table body. The ROW should be a list of each column."""
        self.data.append( Row(values, annotations=annotations))

    def add_raw(self,val):
        self.data.append( Raw(val))

    def ncols(self):
        " Return the number of maximum number of cols in the data"
        if self.data:
            return max([row.ncols() for row in self.data if type(row)==Row])
        return 0


    ################################################################

    def format_cell(self,value,colNumber):
        """ Format a value that appears in a given colNumber. The first column Number is 0.
        Returns (value,alignment)
        """
        formatted_value = None
        if value == None:
            return ("",self.LEFT)
        if value == 0 and self.SUPPRESS_ZERO in self.options:
            return ("",self.LEFT)
        if isnumber(value):
            try:
                formatted_value   = self.col_fmt.get(colNumber, self.col_fmt_default).format(value)
                default_alignment = self.DEFAULT_ALIGNMENT_NUMBER
            except (ValueError,TypeError) as e:
                print(str(e))
                print("Format string: ",self.col_fmt.get(colNumber, self.col_fmt_default))
                print("Value:         ",value)
                print("Will use default formatting")
                pass            # will be formatted below

        if not formatted_value:
            formatted_value   = str(value)
            default_alignment = self.DEFAULT_ALIGNMENT_STRING 
        return (formatted_value, self.col_alignment.get(colNumber, default_alignment))

    def col_formatted_width(self,colNum):
        " Returns the width of column number colNum "
        maxColWidth = 0
        for r in self.col_headings:
            try:
                maxColWidth = max(maxColWidth, len(self.format_cell(r[colNum],colNum)[0]))
            except IndexError:
                pass
        for r in self.data:
            try:
                maxColWidth = max(maxColWidth, len(self.format_cell(r[colNum],colNum)[0]))
            except IndexError:
                pass
        return maxColWidth

    ################################################################

    def typeset_hr(self):
        "Output a HR."
        if self.mode == self.LATEX:
            return "\\hline\n "
        elif self.mode == self.TEXT:
            return "+".join(["-"*self.col_formatted_width(col) for col in range(0,self.cols)]) + "\n"
        elif self.mode == self.HTML:
            return ""                   # don't insert
        raise ValueError("Unknown mode '{}'".format(self.mode))        

    def typeset_cell(self,formattedValue,colNumber):
        "Typeset a value for a given column number."
        import math
        align = self.col_alignment.get(colNumber,self.LEFT)
        if self.mode == self.HTML:  return formattedValue
        if self.mode == self.LATEX: 
            if self.OPTION_NO_ESCAPE in self.options:
                return formattedValue
            else:
                return latex_tools.latex_escape(formattedValue)
        if self.mode == self.TEXT: 
            try:
                fill = (self.col_formatted_widths[colNumber]-len(formattedValue))
            except IndexError:
                fill=0
            if align == self.RIGHT:
                return " "*fill+formattedValue
            if align == self.CENTER:
                return " "*math.ceil(fill/2.0)+formattedValue+" "*math.floor(fill/2.0)
            # Must be LEFT
            if colNumber != self.cols-1: # not the last column
                return formattedValue + " "*fill
            return formattedValue               #  don't indent last column


    def typeset_row(self,row,html_delim='td'):
        "row is a an array. It should be typset. Return the string. "
        ret = []
        if isinstance(row,Raw):
            return row.data
        # if self.mode == self.HTML:
        #     return row.data
        if self.mode == self.HTML:
            ret.append("<tr>")
        for colNumber in range(0,len(row)):
            if colNumber > 0:
                if self.mode == self.LATEX:
                    ret.append(" & ")
                ret.append(" "*self.col_margin)
            (fmt,just)      = self.format_cell(row[colNumber],colNumber)
            val             = self.typeset_cell(fmt,colNumber)

            if self.mode == self.TEXT:
                ret.append(val)
            elif self.mode == self.LATEX:
                if row.annotations:
                    ret.append( row.annotations[colNumber])
                ret.append(val.replace('%','\\%'))
            elif self.mode == self.HTML:
                ret.append(f'<{html_delim} {self.HTML_ALIGNMENT[just]}>{val}</{html_delim}>')
        if self.mode == self.HTML:
            ret.append("</tr>")
        ret.append(self.NL[self.mode])
        return "".join(ret)

    ################################################################

    def calculate_col_formatted_widths(self):
        " Calculate the width of each formatted column and return the array "
        self.col_formatted_widths = []
        for i in range(0,self.cols):
            self.col_formatted_widths.append(self.col_formatted_width(i))
        return self.col_formatted_widths

    def should_omit_row(self,row):
        for (a,b) in self.omit_row:
            if row[a] == b: return True
        return False

    def compute_and_add_col_totals(self):
        " Add totals for the specified cols"
        self.cols = self.ncols()
        totals = [0] * self.cols
        try:
            for r in self.data:
                if self.should_omit_row(r):
                    continue
                if r == self.HR:
                    continue        # can't total HRs
                for col in self.col_totals:
                    if r[col] == '': continue
                    totals[col] += r[col]
        except (ValueError,TypeError) as e:
            print("*** Table cannot be totaled",file=sys.stderr)
            for row in self.data:
                print(row.data,file=sys.stderr)
            raise e
        row = ["Total"]
        for col in range(1,self.cols):
            if col in self.col_totals:
                row.append(totals[col])
            else:
                row.append("")
        self.add_data(self.HR)
        self.add_data(row)
        self.add_data(self.HR)
        self.add_data(self.HR)

    ################################################################
    def typeset_headings(self):
        #
        # Typeset the headings
        #
        ret = []
        if self.col_headings:
            for heading_row in self.col_headings:
                ret.append( self.typeset_row(heading_row,html_delim='th') )
            for i in range(0,self.heading_hr_count):
                ret.append(self.typeset_hr())
        return ret
        
    def typeset(self,*,mode=None,option=None,out=None):
        """ Returns the typset output of the entire table. Builds it up in """

        if ((self.OPTION_LONGTABLE in self.options) and
            (self.OPTION_TABULARX in self.options)):
            raise RuntimeError("OPTION_LONGTABLE and OPTION_TABULARX conflict")

        if len(self.data) == 0:
            print("typeset: no rows")
            return ""

        if mode:
            self.set_mode(mode)
        if self.mode not in [self.TEXT,self.LATEX,self.HTML]:
            raise ValueError("Invalid typsetting mode "+self.mode)

        if option:
            self.add_option(option)
            print("add option",option)
        self.cols = self.ncols() # cache
        if self.cols == 0:
            print("typeset: no data")
            return ""

        if self.mode not in [self.TEXT,self.LATEX,self.HTML]:
            raise ValueError("Invalid typsetting mode "+self.mode)

        if self.mode not in [self.TEXT,self.LATEX,self.HTML]:
            raise ValueError("Invalid typsetting mode "+self.mode)

        ret = [""]              # array of strings that will be concatenatted

        # If we need column totals, compute them
        if hasattr(self,"col_totals"):
            self.compute_and_add_col_totals()

        # Precalc any table widths if necessary 
        if self.mode == self.TEXT:
            self.calculate_col_formatted_widths()
            if self.title:
                ret.append(self.title + ":" + "\n")


        #
        # Start of the table 
        #
        if self.mode == self.LATEX:
            if self.fontsize:
                ret.append("{\\fontsize{%d}{%d}\\selectfont" % (self.fontsize,self.fontsize+1))
            try:
                colspec = self.latex_colspec
            except AttributeError:
                colspec = "r"*self.cols 
            if self.OPTION_LONGTABLE not in self.options:
                # Regular table
                if self.OPTION_TABLE in self.options:
                    ret.append("\\begin{table}")
                if self.OPTION_CENTER in self.options:
                    ret.append("\\begin{center}")
                if self.caption:
                    ret += ["\\caption{",self.caption, "}\n"]
                if self.label:
                    ret.append("\\label{")
                    ret.append(self.label)
                    ret.append("}")
                if self.OPTION_TABULARX in self.options:
                    ret += ["\\begin{tabularx}{\\textwidth}{",colspec,"}\n"]
                else:
                    ret += ["\\begin{tabular}{",colspec,"}\n"]
                ret += self.typeset_headings()
            if self.OPTION_LONGTABLE in self.options:
                # Longtable
                ret += ["\\begin{longtable}{",colspec,"}\n"]
                if self.caption:
                    ret += ["\\caption{",self.caption,"}\\\\ \n"]
                if self.label:
                    ret += ["\\label{",self.label,"}"]
                ret += self.typeset_headings()
                ret.append("\\hline\\endfirsthead\n")
                if self.label:
                    ret += [r'\multicolumn{',str(self.ncols()),r'}{c}{(Table \ref{',self.label,r'} continued)}\\','\n']
                ret += self.typeset_headings()
                ret.append("\\hline\\endhead\n")
                ret += ['\\multicolumn{',str(self.ncols()),'}{c}{(Continued on next page)}\\\\ \n']
                ret.append(self.footer)
                ret.append("\\hline\\endfoot\n")
                ret.append(self.footer)
                ret.append("\\hline\\hline\\endlastfoot\n")
        elif self.mode == self.HTML:
            ret.append("<table>\n")
            ret += self.typeset_headings()
        elif self.mode == self.TEXT:
            if self.caption: 
                ret.append("================ {} ================\n".format(self.caption))
            if self.header:
                ret.append(self.header)
                ret.append("\n")
            ret += self.typeset_headings()


        #
        # typeset each row.
        # computes the width of each row if necessary
        #
        for row in self.data:

            # See if we should omit this row
            if self.should_omit_row(row):
                continue

            # See if this row demands special processing
            if row.data == self.HR:
                ret.append(self.typeset_hr())
                continue

            ret.append(self.typeset_row(row))

        #
        # End of the table
        ##

        if self.mode == self.LATEX:
            if self.OPTION_LONGTABLE not in self.options:
                if self.OPTION_TABULARX in self.options:
                    ret.append("\\end{tabularx}\n")
                else:
                    ret.append("\\end{tabular}\n")
                if self.OPTION_CENTER in self.options:
                    ret.append("\\end{center}")
                if self.OPTION_TABLE in self.options:
                    ret.append("\\end{table}")
            else:
                ret.append("\\end{longtable}\n")
            if self.fontsize:
                ret.append("}")
            if self.footnote:
                ret.append("\\footnote{")
                ret.append( latex_tools.latex_escape(self.footnote) )
                ret.append("}")
        elif self.mode == self.HTML:
            ret.append("</table>\n")
        elif self.mode == self.TEXT:
            if self.footer:
                ret.append(self.footer)
                ret.append("\n")

        # Finally, add any variables that have been defined
        for (name,value) in self.variables.items():
            if self.mode == self.LATEX:
                ret += latex_var(name,value)
            if self.mode == self.HTML:
                ret += "".join(["Note: ",name," is ", value, "<br>"])

        outbuffer = "".join(ret)
        if out:
            out.write(outbuffer)
        return outbuffer

    def add_variable(self,name,value):
        self.variables[name] = value

    def save_table(self,fname,mode=LATEX,option=None):
        with open(fname,"w") as f:
            f.write(self.typeset(mode=mode,option=option))

    def add_sql( self, db, stmt, headings=None, footnote=False ):
        if footnote:
            self.footnote = stmt
        cur = db.cursor()
        try:
            cur.execute( stmt )
        except sqlite3.OperationalError:
            raise RuntimeError("Invalid SQL statement: "+stmt)
        if headings:
            self.add_head( headings )
        else:
            self.add_head( [col[0] for col in cur.description] )
        [ self.add_data(row) for row in cur ]
            
def demo():
    doc = tytable()
    doc.add_head(['State','Abbreviation','Population'])
    doc.add_data(['Virginia','VA',8001045])
    doc.add_data(['California','CA',37252895])
    return doc


if __name__=="__main__":
    # Showcase different ways of making a document and render it each way:
    doc = demo()
    print(doc.prettyprint())
    exit(0)

