#!/usr/bin/env python3
"""
tydoc.py:

Module for typesetting documents in ASCII, LaTeX, and HTML.  Perhaps even CSV!

Simson Garfinkel, 2019-

This python is getting better, but still, please let me clean it up before you copy it.
Documents are stored internally as a python XML Element Tree, with these modifications:

- For many tags, we use a subclass of xml.etree.ElementTree that adds more methods.
- Some metadata that's important for LaTeX is stored as attributes in the nodes.
- Although you *can* use ET.tostring() to generate HTML, this module has a set of rendering
  classes that can save as HTML, MarkDown or LaTeX, and that make prettier HTML.

Special classes to consider:

TyTag - subclass of xml.etree.ElementTree, supports an options
        framework that includes round-tripping into HTML. Options are text
        tags that can be added or removed to control how something formats or
        is typeset.

tydoc   - the root element. Typesets as <html>.
          Includes methods to make it easy to construct complex text documents.


tytable - a class for tables. Lots of methods for adding content and formatting.

Output formats:

HTML - It's not just the DOM; we edit it on output to add functionality. Does not support round-tripping.

LaTeX - Original purpose for this package, makes it easy to create
   LaTeX tables that can be inserted into your documents. Or make the
   whole document!

Markdown - Generally we follow:
  * https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet#links


V2 Rendierng System:

The V2 rendering system will separate the three activities of:
- Representing documents
- Building documents
- Rendering documents



V1 Rendering System:

top-level rendering is done with a function called render(doc,f, format)
The TyTag has a convenience method .render(self, f, format) that simply calls render().
render() recursively renders the tree in the requested format to file f.

To render, we walk the tree.
  - For each tag:
    - If the tag has a CUSTOM RENDERER attribute, call that attribute as a function
      and return. This allows custom tags to control their rendering and avoid the entire machinery.
    - If the tag declares a function called write_tag_begin() to create the start-string for the tag:
      -  it is called.
         - If it returns a result, the result emitted.
      - Otherwise, the renderer's class write_tag_begin() is called to come up with the text
        that is produced as the beginning of the tag.

    - The renderer's text function is called for the tag's text.
    - Each of the tag's children are rendered recursively
    - Renderer's text funciton is called for the tag's tail text.

    - If the tag declares a function called write_tag_end() to create the end-string for the tag:
      -  it is called.
         - If it returns a result, the result emitted.
      - Otherwise, the renderer's class write_tag_end() is called to come up with the text
        that is produced as the beginning of the tag.

Things still needed:

-- TYTABLE --
* Column-based formats
* Automatic formatting of numbers, titles and text
* More sensible handling of spans.


"""

__version__ = "0.2.0"

import xml.etree.ElementTree as ET
import copy
import io
import base64
import codecs
import os
import os.path
import sys
import uuid
import json
import logging
import urllib
import cgi

import random
import string

from collections import defaultdict

from pprint import pformat

from os.path import dirname,abspath
MY_DIR = dirname(abspath(__file__))
if MY_DIR not in sys.path:
    sys.path.append( MY_DIR )

from latex_tools import latex_escape


TAG_HEAD = 'HEAD'
TAG_BODY = 'BODY'
TAG_P = 'P'
TAG_B = 'B'
TAG_I = 'I'
TAG_H1 = 'H1'
TAG_H2 = 'H2'
TAG_H3 = 'H3'
TAG_DIV = 'DIV'
TAG_HTML = 'HTML'
TAG_PRE  = 'PRE'
TAG_TR   = 'TR'
TAG_TH   = 'TH'
TAG_TD   = 'TD'
TAG_TIGNORE = 'X:IGNORE'
TAG_HR   = 'HR'
TAG_UL   = 'UL'
TAG_OL   = 'OL'
TAG_LI   = 'LI'
TAG_A    = 'A'
TAG_TABLE = 'TABLE'
TAG_TITLE = 'TITLE'
TAG_CAPTION = 'CAPTION'
TAG_THEAD = 'THEAD'
TAG_TBODY = 'TBODY'
TAG_TFOOT = 'TFOOT'
TAG_X_TOC = 'X-TOC'  # a custom tag; should not appear in output
TAG_LINK  = 'LINK'
TAG_SCRIPT = 'SCRIPT'
TAG_SPAN   = 'SPAN'

# Automatically put a newline in the HTML stream after one of these tag blocks
HTML_NO_NEWLINE_TAGS = set([TAG_B, TAG_I, TAG_TD, TAG_TH, TAG_A])

ATTR_VAL  = 'v'               # where we keep the original values
ATTR_TYPE = 't'              # the Python type of the value
ATTR_COLSPAN = 'COLSPAN'

ATTRIB_OPTIONS = 'OPTIONS'
ATTRIB_ALIGN = 'ALIGN'

FORMAT_HTML     = 'html'
FORMAT_LATEX    = 'latex'
FORMAT_TEX      = 'tex'
FORMAT_JSON     = 'json'
FORMAT_MARKDOWN = 'md'
FORMAT_CSV      = 'csv'
FORMAT_OPENPYXL = 'openpyxl'

CUSTOM_RENDERER = 'custom_renderer'
CUSTOM_WRITE_TEXT = 'custom_write_text'

# Automatically put a newline in the HTML stream after one of these tag blocks

HTML_START_NEWLINE_TAGS = {TAG_HEAD, TAG_HTML, TAG_BODY, TAG_TABLE, TAG_CAPTION, TAG_THEAD, TAG_TBODY, TAG_TFOOT}
HTML_END_NO_NEWLINE_TAGS = {TAG_B, TAG_I, TAG_TD, TAG_TH, TAG_A}
FLOAT_TYPES = set(['float', 'float32', 'float64'])
INTEGER_TYPES = set(['int', 'int32', 'int64'])


LATEX_TAGS = {TAG_P: ('\n', '\n\n'),
              TAG_PRE: ('\\begin{Verbatim}\n', '\n\\end{Verbatim}\n'),
              TAG_B: ('\\textbf{', '}'),
              TAG_I: ('\\textit{', '}'),
              TAG_H1: ('\\section{', '}\n'),
              TAG_H2: ('\\subsection{', '}\n'),
              TAG_H3: ('\\subsubsection{', '}\n'),
              TAG_HR: ('', ''),
              # do something better
              TAG_HEAD: ('', ''),
              TAG_BODY: ('', ''),
              TAG_UL: ('\\begin{itemize}\n', '\\end{itemize}\n'),
              TAG_OL: ('\\begin{enumerate}\n', '\\end{enumerate}\n'),
              TAG_LI: ('\\item ', ''),
              TAG_TITLE: ('\\title{', '}\n\\maketitle\n')}


MARKDOWN_TAGS = {TAG_HTML: ('', ''),
                 TAG_PRE: ("```", "```"),
                 TAG_TITLE: ('# ', '\n'),
                 TAG_P: ('', '\n\n'),
                 TAG_B: ('**', '**'),
                 TAG_H1: ('# ', '\n'),
                 TAG_H2: ('## ', '\n'),
                 TAG_H3: ('### ', '\n'),
                 TAG_HR: ('=' * 64, '\n'),
                 TAG_HEAD: ('', ''),
                 TAG_BODY: ('', ''),
                 TAG_UL: ('', ''),  # should set a flag.
                 TAG_OL: ('', ''),  # should set a different flag
                 TAG_LI: ('* ', '\n'),  # should read the flag
                 }

# For the Python
OPTION_LONGTABLE = 'longtable'  # use LaTeX {longtable} environment
OPTION_TABLE     = 'table'    # use LaTeX {table} enviornment
OPTION_TABULARX  = 'tabularx'  # use LaTeX {tabularx} environment
OPTION_CENTER    = 'center'   # use LaTeX {center} environment
OPTION_NO_ESCAPE = 'noescape'  # do not escape LaTeX values
OPTION_SUPPRESS_ZERO    = "suppress_zero"  # suppress zeros

ATTRIB_LATEX_COLSPEC  = 'latex_colspec'
ATTRIB_TEXT_FORMAT = 'TEXT_FORMAT'
ATTRIB_FLOAT_FORMAT = 'FLOAT_FORMAT'
ATTRIB_INTEGER_FORMAT = 'INTEGER_FORMAT'
ATTRIB_FONT_SIZE = 'FONTSIZE'
ATTRIB_TITLE = 'TITLE'
ATTRIB_FOOTER = 'FOOTER'
ATTRIB_LABEL = 'LABEL'

# For the Python table maker


ALIGN_LEFT = "LEFT"
ALIGN_CENTER = "CENTER"
ALIGN_RIGHT = "RIGHT"

DEFAULT_ALIGNMENT_NUMBER = ALIGN_RIGHT
DEFAULT_ALIGNMENT_STRING = ALIGN_LEFT

DEFAULT_TEXT_FORMAT    = '{}'
DEFAULT_FLOAT_FORMAT   = '{:,}'
DEFAULT_INTEGER_FORMAT = '{:,}'


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}

    children = list(t)

    if children:
        dd = defaultdict(list)

        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)

        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}

    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())

    if t.text:
        text = t.text.strip()

        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text

    return d


def is_empty(elem):
    """Return true if tag has no text or children. Used to turn <tag></tag> into <tag/>.
    Note that the script and link tags can never be made empty"""
    if elem.tag.upper() in [TAG_SCRIPT, TAG_LINK]:
        return False
    return len(elem) == 0 and ((elem.text is None) or (len(elem.text) == 0))

class Renderer:
    @staticmethod
    def format():
        return None

    # By default, we write the tag as is repr()
    @staticmethod
    def write_tag_begin(doc, f):
        f.write(f'{repr(doc)}\n')
        return True

    # Default write_text just writes the text
    @staticmethod
    def write_text(doc, f, text=None):
        if text is None:
            text = doc.text
        if text is not None:
            f.write(text)
        return True

    # By default, we write that we are at the end of the tag
    @staticmethod
    def write_tag_end(doc, f):
        f.write(f'--- end repr(doc) ---\n')
        return True

    # By default, we write the tail to output
    @staticmethod
    def write_tail(doc, f, tail=None):
        if tail is None:
            tail = doc.tail
        if tail is not None:
            f.write(tail)
        return True


class HTMLRenderer(Renderer):
    """Render the HTML tags, but just write the text and the tail."""

    @staticmethod
    def format():
        return FORMAT_HTML

    @staticmethod
    def write_tag_begin(doc, f):
        if doc.tag==TAG_TIGNORE:
            return True

        eflag = '/' if is_empty(doc) else ''

        if doc.attrib:
            attribs = (" " + " ".join([f'{key}="{value}"' for (key, value) in doc.attrib.items()]))
        else:
            attribs = ''

        f.write(f'<{doc.tag}{attribs}{eflag}>')

        if doc.tag.upper() in HTML_START_NEWLINE_TAGS:
            f.write("\n")

        return True

    @staticmethod
    def write_tag_end(doc, f):
        if doc.tag==TAG_TIGNORE:
            return True
        if not is_empty(doc):
            f.write(f'</{doc.tag}>')
            if doc.tag.upper() not in HTML_END_NO_NEWLINE_TAGS:
                f.write("\n")
        return True


class LatexRenderer(Renderer):
    @staticmethod
    def format():
        return FORMAT_LATEX

    @staticmethod
    def write_tag_begin(doc, f):
        tag = doc.tag.upper()
        try:
            (begin, end) = LATEX_TAGS[tag]
            f.write(begin)
        except KeyError as e:
            f.write(f"\n% <{tag}>\n")
        return True

    @staticmethod
    def write_text(doc, f, text=None):
        if text is None:
            text = doc.text
        if text is not None:
            if hasattr(doc, 'option') and doc.option(OPTION_NO_ESCAPE):
                f.write(latex_escape(text))
            else:
                f.write(text)

    @staticmethod
    def write_tag_end(doc, f):
        tag = doc.tag.upper()
        try:
            (begin, end) = LATEX_TAGS[doc.tag.upper()]
            f.write(end)
        except KeyError as e:
            f.write(f"\n% </{tag}>\n")
        return True

    @staticmethod
    def write_tail(doc, f, tail=None):
        if tail is None:
            tail = doc.tail
        if tail is not None:
            if hasattr(doc, 'option') and doc.option(OPTION_NO_ESCAPE):
                f.write(latex_escape(tail))
            else:
                f.write(tail)

class MarkdownRenderer(Renderer):
    @staticmethod
    def format():
        return FORMAT_MARKDOWN

    @staticmethod
    def write_tag_begin(doc, f):
        try:
            (begin, end) = MARKDOWN_TAGS[doc.tag.upper()]
            f.write(begin)
        except KeyError as e:
            pass
        return True

    @staticmethod
    def write_tag_end(doc, f):
        try:
            (begin, end) = MARKDOWN_TAGS[doc.tag.upper()]
            f.write(end)
        except KeyError as e:
            pass
        return True

class JsonRenderer(Renderer):
    @staticmethod
    def format():
        return FORMAT_JSON


RENDERERS = {FORMAT_HTML: HTMLRenderer(),
             FORMAT_LATEX: LatexRenderer(),
             FORMAT_TEX: LatexRenderer(),
             FORMAT_MARKDOWN: MarkdownRenderer(),
             FORMAT_JSON: JsonRenderer()}


def render(doc, f, format=FORMAT_HTML):
    """
    Custom rendering tool. Use the built-in rendering unless the
    Element has its own render method. Write results to f, which can
    be a file or an iobuffer.
    """

    if hasattr(doc, CUSTOM_RENDERER) and doc.custom_renderer(f, format=format):
        return True

    try:
        r = RENDERERS[format]
    except KeyError as e:
        raise RuntimeError("Unsupported format: " + format)

    if not (hasattr(doc, "write_tag_begin") and doc.write_tag_begin(f, format)):
        r.write_tag_begin(doc, f)

    if not (hasattr(doc, "write_text") and doc.write_text(f, format)):
        r.write_text(doc, f)

    for child in list(doc):
        render(child, f, format)

    if not (hasattr(doc, "write_tag_end") and doc.write_tag_end(f, format)):
        r.write_tag_end(doc, f)

    if doc.tail is not None:
        if not (hasattr(doc, "write_tail") and doc.write_tail(f, format)):
            r.write_tail(doc, f)


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

class TyTag(ET.Element):
    """ctools HTML tag class, with support for rendering and creation."""

    def __init__(self, tag, attrib={}, text=None, **extra):
        """Create a tag. If text is provided, make that the tag's text"""
        super().__init__(tag, attrib, **extra)
        if text is not None:
            self.text = text

    def render(self, f, format='html'):
        """Write to f in specified format. Uses the render system defined above."""
        return render(self, f, format=format)

    def save(self, f_or_fname, format=None):
        """
        Save to a filename or a file-like object
        @param f_or_fname - a filename or a file-like object.
        @param format     - the format to use. Will learn from fname's extension if None
        """

        if format is None:
            # Learn format
            format = os.path.splitext(f_or_fname)[1].lower()
            if format[0:1] == '.':
                format = format[1:]

        if hasattr(f_or_fname, 'write'):
            self.render(f_or_fname, format=format)
            return

        with open(f_or_fname, "w") as f:
            self.render(f, format=format)
            return

    def asString(self, format='html'):
        """Return the tag as a string"""
        if format is None:
            raise ValueError("format must be specified")

        s = io.StringIO()
        self.render(s, format=format)
        return s.getvalue()

    def prettyprint(self):
        import xml.dom.minidom
        s = ET.tostring(self, encoding='unicode')
        return xml.dom.minidom.parseString(s).toprettyxml(indent='  ')

    def options_as_set(self):
        """Return all of the options as a set"""
        try:
            return set(self.attrib[ATTRIB_OPTIONS].split(','))
        except KeyError as e:
            return set()

    def set_option(self, option):
        """@param option is a string that is added to the 'option' attrib.
        They are separated by commas"""
        options = self.options_as_set()
        options.add(option)
        self.attrib[ATTRIB_OPTIONS] = ','.join(options)
        return self

    def clear_option(self, option):
        """@param option is a string that is added to the 'option' attrib.
        They are separated by commas"""
        options = self.options_as_set()
        options.remove(option)
        self.attrib[ATTRIB_OPTIONS] = ','.join(options)
        return self

    def option(self, option):
        """Return true if option is set."""
        return option in self.options_as_set()

    def set_attrib(self, newAttribs):
        assert isinstance(newAttribs, dict)
        self.attrib = {**self.attrib, **newAttribs}
        return self

    def setText(self, text):
        self.text = text
        return self

    def add_tag_elems(self, tag, elems=[], attrib={}, position=-1, id=None, className=None):
        """
        Add an element with option children.
        @param tag   - if text, create a new tag with tag tag.
                     - if a TyTag instance, just use it.
        @param elems - If elems[0] is text, make it the child text.
                     - If elems[:] haselements inside it, add them as subelements
                     - If elems[-1] is text, make it the tail.
        @param id    - convenience method to specify attrib['id']
        @param className - convenience method to specify attrib['class']
        Returns the tag that is added.

        note: no **kwargs because we want args that are improperly provided to raise an error.
        """

        if id is not None:
            if 'id' in attrib:
                raise ValueError("id parameter specified and 'id' present in attrib: " +str(attrib))
            attrib['id'] = id

        if className is not None:
            if 'class' in attrib:
                raise ValueError("id parameter specified and 'class' present in attrib: " +str(attrib))
            attrib['class'] = className

        # Mutable default value for attrib is ok, since we're not
        # changing attrib here or in any subclasses

        # Make the tag and add it. The add in the text or sub-tags
        assert isinstance(elems, list)

        if isinstance(tag, TyTag):
            e = tag
        else:
            if tag[0] == '<':
                raise ValueError(f'tag {tag} should not include angle brackets.')
            e = TyTag(tag, attrib=attrib)
        if position == -1:
            self.append(e)
        else:
            self.insert(position, e)

        lastTag = None
        for elem in elems:
            if not isinstance(elem, ET.Element):
                if lastTag is None:
                    if e.text == None:
                        e.text = ""
                    e.text += str(elem)
                else:
                    if lastTag.tail  == None:
                        lastTag.tail = ""
                    lastTag.tail  += str(elem)
            else:
                # Copy the tag into place
                lastTag = copy.deepcopy(elem)
                e.append(lastTag)
        return e

    def add_tag(self, tag, attrib={}, position=-1, **kwargs):
        return self.add_tag_elems(tag, elems=[], attrib=attrib, position=position, **kwargs)

    def add_tag_text(self, tag, text='', attrib={}, position=-1, **kwargs):
        """Like add_tag_elems above, but just with the text for tag. Calls add_tag_elems"""
        return self.add_tag_elems(tag, [text], attrib=attrib, position=position, **kwargs)

    def append_image(self, buf, *, format):
        if isinstance(buf, io.BytesIO):
            buf.seek(0)
            buf = buf.read()  # turn it into a buffer
        img = EmbeddedImageTag(buf, format=format)
        self.add_tag(img)

    def append_matplotlib(self, fig, *, format="png", **kwargs):
        buf = io.BytesIO()
        fig.savefig(buf, format=format, **kwargs)
        buf.seek(0)
        self.append_image(buf, format='png')

    # convenience classes add to body if present, otherwise add local
    def body_(self):
        return self.body if hasattr(self, 'body') else self

    def p(self, text='', **kwargs):
        """Add a paragraph. Multiple arguments are combined
        and can be text or other HTML elements"""
        return self.body_().add_tag_text(TAG_P, text, **kwargs)

    def a(self, text='', **kwargs):
        """Add a link"""
        return self.body_().add_tag_text(TAG_A, text, **kwargs)

    def h1(self, text='', **kwargs):
        """Append H1 to the current tag"""
        return self.body_().add_tag_text(TAG_H1, text, **kwargs)

    def h2(self, text='', **kwargs):
        """Add a H2"""
        return self.body_().add_tag_text(TAG_H2, text, **kwargs)

    def h3(self, text='', **kwargs):
        """Add a H3"""
        return self.body_().add_tag_text(TAG_H3, text, **kwargs)

    def div(self, text='', **kwargs):
        return self.body_().add_tag_text(TAG_DIV, text, **kwargs)

    def pre(self, text='', **kwargs):
        """Add a preformatted"""
        return self.body_().add_tag_text(TAG_PRE, text, **kwargs)

    def a(self, text='', **kwargs):
        """Add a link"""
        return self.body_().add_tag_text(TAG_A, text, **kwargs)

    def b(self, text='', **kwargs):
        """Add bold"""
        return self.body_().add_tag_text(TAG_B, text, **kwargs)

    def hr(self, **kwargs):
        """Add a horizontal rule"""
        return self.add_tag_text(TAG_HR, **kwargs)

    def table(self, **kwargs):
        t = tytable(**kwargs)
        self.body_().append(t)
        return t

    def json_table(self, **kwargs):
        t = jsonTable(**kwargs)
        self.body_().append(t)
        return t

    def ul(self, text='', **kwargs):
        """Add a UL"""
        return self.body_().add_tag_text(TAG_UL, text, **kwargs)

    def li(self, text='', **kwargs):
        """Add a LI"""
        return self.body_().add_tag_text(TAG_UL, text, **kwargs)

    def span(self, text='', **kwargs):
        return self.body_().add_tag_text(TAG_SPAN, text, **kwargs)


class EmbeddedImageTag(TyTag):
    def __init__(self, buf, *, format, alt=""):
        """Create an image. You must specify the format.
        buf can be a string of a BytesIO"""
        super().__init__('img')
        self.buf = buf
        self.alt = alt
        self.format = format

    def custom_renderer(self, f, alt="", format=FORMAT_HTML):
        if format == FORMAT_HTML:
            f.write('<img alt="{}" src="data:image/{};base64,{}" />'.
                    format(self.alt, self.format, codecs.decode(base64.b64encode(self.buf))))
        elif format in (FORMAT_LATEX, FORMAT_TEX):
            fname = os.path.splitext(f.name)[0] + "_image.png"
            with open(fname, "wb") as f2:
                f2.write(self.buf)
            f.write(f'\\includegraphics{fname}\n')
        elif format == FORMAT_MARKDOWN:
            fname = os.path.splitext(f.name)[0] + "_image.png"
            with open(fname, "wb") as f2:
                f2.write(self.buf)
            f.write(f'![{fname}]({fname})\n')
        else:
            raise RuntimeError("unknown format: {}".format(format))

class tydoc(TyTag):
    """
    Python class for building HTML documents and rendering them into
    HTML, LaTeX or Markdown. Contains two sub-elements: head and body.
    Note that you don't want to append to tydoc you want to append to the head or body.
    """

    # We have a custom begin and end text for latex

    DEFAULT_LATEX_PACKAGES = ['graphicx', 'tabularx', 'longtable']
    DEFAULT_META_TAGS = ['<meta http-equiv="Content-type" content="text/html; charset=utf-8">']

    def __init__(self):
        super().__init__(TAG_HTML)
        self.head    = self.add_tag_elems(TAG_HEAD)
        self.body    = self.add_tag_elems(TAG_BODY)
        self.latex_packages = self.DEFAULT_LATEX_PACKAGES

    def write_tag_begin(self, f, format=None):
        """Provide custom tags for writing document tag"""
        if format == FORMAT_LATEX:
            f.write("\n".join(["\\documentclass{article}"]
                              + ['\\usepackage{%s}\n' % pkg for pkg in self.latex_packages]
                              + ["\\begin{document}"]))
            return True
        elif format == FORMAT_HTML:
            f.write('\n'.join(['<!DOCTYPE html>', '<html lang="en">'] + self.DEFAULT_META_TAGS))
            f.write('\n')
            return True
        else:
            return False

    @staticmethod
    def write_tag_end(f, format=None):
        if format == FORMAT_LATEX:
            f.write("\\end{document}\n")
            return True
        elif format == FORMAT_HTML:
            f.write('</html>\n')
            return True
        else:
            return False

    def title(self, text, **kwargs):
        self.head.add_tag_elems(TAG_TITLE, [text], **kwargs)

    def insert_toc(self, level=3):
        # If there is already a TOC tag, remove it, then add a new one.
        for body in self.findall(f"./{TAG_BODY}"):
            for xtoc in body.findall(f"./{TAG_X_TOC}"):
                body.remove(xtoc)

        # Render the DOC as HTML and grab all of the H1, H2 and H3 tags to build the TOC
        xml_data = io.StringIO()
        xml_data.write(f"<UL>")
        current_level = 1
        body = self.find("./BODY")

        for elem in list(body):
            if elem.tag == TAG_H1 and level >= 1:
                new_level = 1
            elif elem.tag == TAG_H2 and level >= 2:
                new_level = 2
            elif elem.tag == TAG_H3 and level >= 3:
                new_level = 3
            else:
                continue

            while new_level > current_level:
                xml_data.write("<UL>")
                current_level += 1

            while new_level < current_level:
                xml_data.write("</UL>")
                current_level -= 1

            xml_data.write(f"<LI><A HREF='#{id(elem)}'>{elem.text}</A></LI>")

            # add the <a name=> anchor tag if none is present
            a_tag = elem.find("{}[@NAME='{}']".format(TAG_A, id(elem)))

            if a_tag is None:
                a_tag = ET.SubElement(elem, TAG_A, {'NAME': str(id(elem))})
                # Move the text to after the a_tag
                a_tag.tail = elem.text
                elem.text = ''

        while current_level > 1:
            xml_data.write("</UL>")
            current_level -= 1

        xml_data.write(f"</UL>")

        # Parse it and add to an X_TOC tag.
        xml_data.seek(0)
        xtoc = X_TOC()
        xtoc.insert(0, ET.XML(xml_data.read()))

        # And add it to the body
        body.insert(0, xtoc)

    def add_stylesheet(self, url):
        self.head.append(TyTag('link', {'rel': "stylesheet", 'type': "text/css", 'href': url}))

    def add_script(self, url):
        self.head.append(TyTag('script', {'type': "text/javascript", 'src': url}))

class html(tydoc):
    """We can also call the tydoc an html file"""
    pass

################################################################
# Tag to typeset Table of Contents.
# HTML and Markdown get passed through.
# LaTeX gets changed to \maketableofcontents and ignores the content
################################################################
class X_TOC(TyTag):
    def __init__(self, attrib={}, **extra):
        """Mutable default value for attrib is ok, since we're not changing attrib here or in any subclasses"""
        super().__init__(TAG_X_TOC, attrib=attrib, **extra)

    @staticmethod
    def custom_renderer(f, format=FORMAT_HTML):
        if format in (FORMAT_LATEX, FORMAT_TEX):
            f.write("\\tableofcontents\n")
            return True
        return False

    @staticmethod
    def write_tag_begin(f, format=FORMAT_HTML):
        if format == FORMAT_HTML:
            # Output nothing
            return True
        return False

    @staticmethod
    def write_tag_end(f, format=FORMAT_HTML):
        if format == FORMAT_HTML:
            # Output nothing
            return True
        return False


def tag_ignore():
    return ET.Element(TAG_TIGNORE)


################################################################
# Tables can then be rendered into JSON or another form.
################################################################

class jsonTable(TyTag):

    VALID_ALIGNS = {ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT}

    @staticmethod
    def cells_in_row(tr):
        return list(filter(lambda t: t.tag in (TAG_TH, TAG_TD, TAG_TIGNORE), tr))

    def __init__(self, attrib={}, **extra):
        # Mutable default value for attrib is ok, since we're not changing attrib here or in any subclasses
        super().__init__(TAG_TABLE, attrib=attrib, **extra)

        self.attrib[ATTRIB_TEXT_FORMAT]    = DEFAULT_TEXT_FORMAT
        self.attrib[ATTRIB_FLOAT_FORMAT]  = DEFAULT_FLOAT_FORMAT
        self.attrib[ATTRIB_INTEGER_FORMAT] = DEFAULT_INTEGER_FORMAT

        # Create the layout of the generic table and create easy methods for accessing
        self.caption = self.add_tag(TAG_CAPTION)
        self.thead   = self.add_tag(TAG_THEAD)
        self.tbody   = self.add_tag(TAG_TBODY)
        self.tfoot   = self.add_tag(TAG_TFOOT)

        # Auto id support
        self.col_auto_ids = None

    def custom_renderer(self, f, format=FORMAT_HTML):
        return self.custom_renderer_json(f)

    def custom_renderer_json(self, f):
        """
        Output the data in the body of the table as a JSON object.
        """
        data = dict()
        for tr in self.findall("./TBODY/TR"):
            for cell in tr:
                if cell.tag==TAG_TIGNORE:
                    continue
                if 'id' not in cell.attrib:  # no tag!
                    continue
                try:
                    if ATTR_VAL in cell.attrib:
                        if cell.attrib[ATTR_TYPE]=='int':
                            data[cell.attrib['id']] = int(cell.attrib[ATTR_VAL])
                        elif cell.attrib[ATTR_TYPE]=='float':
                            data[cell.attrib['id']] = float(cell.attrib[ATTR_VAL])
                        else:
                            data[cell.attrib['id']] = cell.attrib[ATTR_VAL]  # 936
                    else:
                        data[cell.attrib['id']] = cell.text
                except KeyError as e:
                    pass

        f.write(json.dumps(data, indent=4))

        return True

    def set_caption(self, caption):
        #  TODO: Validate that this is first
        """
        The <caption> tag must be inserted immediately after the <table> tag.
        https://www.w3schools.com/tags/tag_caption.asp
        """
        self.add_tag_text(TAG_CAPTION, caption, position=0)

    def set_fontsize(self, size):
        self.attrib[ATTRIB_FONT_SIZE] = str(size)

    #################################################################
    # Cell Formatting Routines

    def format_cell(self, cell):
        """Modify cell by setting its text to be its format. Uses eval, so it's not safe."""

        try:
            typename = cell.attrib[ATTR_TYPE]
            typeval  = urllib.parse.unquote(cell.attrib[ATTR_VAL])
        except KeyError:
            return cell

        if typename is None:
            return cell

        try:
            value = eval(typename)(typeval)
        except (NameError, SyntaxError) as e:
            return cell

        if isinstance(value, ET.Element):
            value = value.text

        try:
            if cell.attrib[ATTR_TYPE] == 'int':
                cell.text = self.attrib[ATTRIB_INTEGER_FORMAT].format(int(value))
                return cell
            elif cell.attrib[ATTR_TYPE] != 'str':
                cell.text = self.attrib[ATTRIB_FLOAT_FORMAT].format(float(value))
                return cell
        except TypeError as e:
            pass
        except ValueError as e:
            pass

        cell.text = self.attrib[ATTRIB_TEXT_FORMAT].format(value)

        return cell

    #################################################################
    # Table Manipulation Routines

    def add_row(self, where, cells, row_attrib={}, row_auto_id=None):
        """
        Add a row of cells to the table.
        You probably want to call add_head(), add_data() or add_foot().

        @param where      - must be TAG_THEAD, TAG_TBODY or TAG_TFOOT
        @param cells      - a list of cells that are added. These are typically Elements made with make_cells()
                            Each will have its id= attribute set if row_auto_id and self.col_auto_ids are set.
        @param row_attrib - the attribute for the row
        """

        # Mutable default value for row_attrib is ok, since we're not changing attrib here or in any subclasses

        assert where in (TAG_THEAD, TAG_TBODY, TAG_TFOOT)

        where_node = self.findall(f".//{where}")[0]

        if row_auto_id is not None:
            row_attrib = {**row_attrib, **{'id': row_auto_id}}
            if self.col_auto_ids is not None:
                for (cell, name) in zip(cells, self.col_auto_ids):
                    cell.attrib['id'] = row_auto_id + "_" + name
            else:
                for (cell, i) in zip(cells, range(len(cells))):
                    cell.attrib['id'] = row_auto_id + "_" + str(i)

        row = ET.SubElement(where_node, TAG_TR, attrib=row_attrib)

        for cell in cells:
            assert isinstance(cell, ET.Element)
            row.append(cell)

            # If cell has COLSPAN>1, then put in placeholder cells that will not render
            try:
                for col in range(1, int(cell.attrib[ATTR_COLSPAN])):
                    row.append(ET.Element(TAG_TIGNORE))
            except KeyError as e:
                pass

    def add_row_values(self, where, tags, values, *, cell_attribs=None, row_attrib=None, row_auto_id=None):
        """
        Create a row of cells and add it to the table. This is called by add_head, add_data, or add_foot.

        @param where  - should be TAG_THEAD/TAG_TBODY/TAG_TFOOT
        @param tags   - a single tag, or a list of tags. If it is a tag, all of the cells are that tag.
        @param values - a list of values, one per column.  Each is automatically formatted.
                        However, if a value is a TD or a TH element, we just copy that element and use it.
        @param cell_attribs - a single cell attrib, or a list of attribs.
                              If a single attrib, it is given to all the cells.
        @param row_attrib   - a single attrib for the row, or a list of attribs
        @param row_auto_id  - the id for the row.
                              Cell IDs will be row-col when rendered if row and col auto_id are provied.
        """
        assert where in (TAG_THEAD, TAG_TBODY, TAG_TFOOT)

        if cell_attribs is None:
            cell_attribs = {}

        if row_attrib is None:
            row_attrib = {}

        # If tags is not a list, make it a list
        if not isinstance(tags, list):
            tags = [tags] * len(values)

        if not isinstance(cell_attribs, list):
            cell_attribs = [cell_attribs] * len(values)

        if not (len(tags) == len(values) == len(cell_attribs)):
            raise ValueError(
                "tags ({}) values ({}) and cell_attribs ({}) must all have same length".format(len(tags), len(values), len(cell_attribs)))

        cells = [self.make_cell(t, v, a) for (t, v, a) in zip(tags, values, cell_attribs)]

        self.add_row(where, cells, row_attrib=row_attrib, row_auto_id=row_auto_id)

    def add_head(self, values, row_attrib=None, cell_attribs=None, col_auto_ids=None, row_auto_id="head"):
        if col_auto_ids is not None:
            if self.col_auto_ids is None:
                self.col_auto_ids = col_auto_ids
            else:
                raise RuntimeError("auto_ids may only be specified once")

        self.add_row_values(TAG_THEAD, 'TH', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id=row_auto_id)

    def add_data(self, values, row_attrib=None, cell_attribs=None, row_auto_id=None):
        self.add_row_values(TAG_TBODY, 'TD', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id=row_auto_id)

    def add_foot(self, values, row_attrib=None, cell_attribs=None):
        self.add_row_values(TAG_TFOOT, 'TD', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id="foot")

    def add_data_array(self, rows):
        for row in rows:
            self.add_data(row)

    def make_cell(self, tag, value, attrib):
        """
        Given a tag, value and attributes, return a cell formatted with the default format.
        If value is a scalar, make and format it. If it is an element, then just make it the children.
        This is called by add_row.

        Note - if value is a ET.Element that is either a TAG_TD or TAG_TH, it will be copied and used, otherwise
               it will be put inside a newly-created TAG_TD or TAG_TH.
        """

        # logging.warning("make_cell(tag=%s,value=%s,attrib=%s)", tag,value,attrib)
        # logging.warning("same: %s",isinstance(value, ET.Element))

        if isinstance(value, ET.Element):
            if value.tag.upper() in [TAG_TH, TAG_TD]:
                cell = copy.copy(value)
                for (k, v) in attrib:
                    cell.attrib[k] = v
            else:
                cell = ET.Element(tag, attrib)
                cell.insert(0, value)

            return cell

        cell = ET.Element(tag, {**attrib, ATTR_VAL: str(value), ATTR_TYPE: str(type(value).__name__)})

        self.format_cell(cell)
        return cell

    ################################################################
    # Table get information routines

    def get_caption(self):
        """Return the <caption> tag text"""
        try:
            c = self.findall(".//CAPTION")
            return c[0].text
        except (KeyError, IndexError) as e:
            return None

    def rows(self):
        """Return the rows"""
        return self.findall(".//TR")

    def row(self, n):
        """Return the nth row; n starts at 0"""
        return self.rows()[n]

    def max_cols(self):
        """Return the number of maximum number of cols in the data. Expensive to calculate"""
        return max(len(row.findall("*")) for row in self.rows())

    def get_cell(self, row, col):
        """Return the cell at row, col; both start at 0"""
        return self.cells_in_row(self.row(row))[col]

    def col(self, n):
        """Returns all the cells in column n"""
        return [row[n] for row in self.rows()]

################################################################
# Improved tytable with the new API.
# Class name has changed from ttable to tytable.
# It now uses the XML ETree to represent the table.
# Tables can then be rendered into HTML or another form.
################################################################
class tytable(TyTag):
    """
    Python class for representing a table that can be rendered into
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

    4. autoid mode adds a ids to rows and columns automatically
    """

    VALID_ALIGNS = {ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT}

    @staticmethod
    def cells_in_row(tr):
        return list(filter(lambda t: t.tag in (TAG_TH, TAG_TD, TAG_TIGNORE), tr))

    def __init__(self, attrib={}, **extra):
        # Mutable default value for attrib is ok, since we're not changing attrib here or in any subclasses
        super().__init__(TAG_TABLE, attrib=attrib, **extra)

        self.attrib[ATTRIB_TEXT_FORMAT]    = DEFAULT_TEXT_FORMAT
        self.attrib[ATTRIB_FLOAT_FORMAT]   = DEFAULT_FLOAT_FORMAT
        self.attrib[ATTRIB_INTEGER_FORMAT] = DEFAULT_INTEGER_FORMAT

        # Create the layout of the generic table and create easy methods for accessing
        self.caption = self.add_tag(TAG_CAPTION)
        self.thead   = self.add_tag(TAG_THEAD)
        self.tbody   = self.add_tag(TAG_TBODY)
        self.tfoot   = self.add_tag(TAG_TFOOT)

        # Autoid support
        self.col_auto_ids = None

    def custom_renderer(self, f, format=FORMAT_HTML):
        if format in (FORMAT_LATEX, FORMAT_TEX):
            return self.custom_renderer_latex(f)
        elif format in (FORMAT_MARKDOWN):
            return self.custom_renderer_md(f)
        elif format in (FORMAT_CSV):
            return self.custom_renderer_csv(f)
        elif format in (FORMAT_JSON):
            return self.custom_renderer_json(f)
        else:
            return False

    def custom_renderer_latex(self, f):
        self.render_latex_table_head(f)
        f.write("\\hline\n")
        self.render_latex_table_body(f)
        f.write("\\hline\n")
        self.render_latex_table_foot(f)
        return True

    def custom_renderer_csv(self, f):
        for section in ["./THEAD/TR", "./TBODY/TR", "./TFOOT/TR"]:
            for tr in self.findall(section):
                f.write(",".join([cell.text for cell in tr]))
                f.write("\n")

        return True

    def custom_renderer_md(self, f):
        """
        Output the table as markdown. Note:
        1. Assumes the first row is the header.
        2. Applies 'strip' to all text columns.
        """

        # Calculate the maxim width of each column
        all_cols = [self.col(n) for n in range(self.max_cols())]
        col_maxwidths = [max([len(str(cell.text).strip()) for cell in col])
                         for col in all_cols]

        for (rownumber, tr) in enumerate(self.findall(".//TR"), 0):
            # Get the cells for this row
            row_cells = self.cells_in_row(tr)

            # Pad this row out if it needs padding
            # Markdown tables don't support col span
            if len(row_cells) < len(all_cols):
                row_cells.extend([TyTag(TAG_TD)] * (len(all_cols) - len(row_cells)))

            # Make up the format string for this row based on the cell attributes

            fmts = []
            for (cell, maxwidth) in zip(row_cells, col_maxwidths):
                if cell.attrib.get(ATTRIB_ALIGN, "") == ALIGN_LEFT:
                    align = '<'
                elif cell.attrib.get(ATTRIB_ALIGN, "") == ALIGN_CENTER:
                    align = '^'
                elif cell.attrib.get(ATTRIB_ALIGN, "") == ALIGN_RIGHT:
                    align = '>'
                else:
                    align = ''

                fmts.append("{:" + align + str(maxwidth) + "}")

            fmt = "|" + "|".join(fmts) + "|\n"

            # Get the text we will format
            row_texts = [cell.text.strip() for cell in row_cells]

            # Write it out, formatted
            f.write(fmt.format(*row_texts))

            # Add a line between the first row and the rest.
            if rownumber == 0:
                lines = ['-' * width for width in col_maxwidths]
                f.write(fmt.format(*lines))

        return True  # we rendered!

    def custom_renderer_json(self, f):
        """Output the data in the body of the table as a JSON object."""
        data = dict()
        for tr in self.findall("./TBODY/TR"):
            for cell in tr:
                if cell.tag==TAG_TIGNORE:
                    continue
                if ATTR_VAL in cell.attrib:
                    if cell.attrib[ATTR_TYPE]=='int':
                        data[cell.attrib['id']] = int(cell.attrib[ATTR_VAL])
                    elif cell.attrib[ATTR_TYPE]=='float':
                        data[cell.attrib['id']] = float(cell.attrib[ATTR_VAL])
                    else:
                        data[cell.attrib['id']] = cell.attrib[ATTR_VAL]
                else:
                    data[cell.attrib['id']] = cell.text  # 1306

        f.write(json.dumps(data))
        return True

    #################################################################
    # LaTeX support routines
    def latex_cell_text(self, cell):
        if self.option(OPTION_NO_ESCAPE):
            return cell.text
        else:
            return latex_escape(cell.text)

    def render_latex_table_row(self, f, tr):
        """Render the first set of rows that were added with the add_head() command"""
        f.write(' & '.join([self.latex_cell_text(cell) for cell in tr]))
        f.write('\\\\\n')

    def render_latex_table_head(self, f):
        if self.option(OPTION_TABLE) and self.option(OPTION_LONGTABLE):
            raise RuntimeError("options TABLE and LONGTABLE conflict")

        if self.option(OPTION_TABULARX) and self.option(OPTION_LONGTABLE):
            raise RuntimeError("options TABULARX and LONGTABLE conflict")

        if self.option(OPTION_TABLE):
            # LaTeX table - a kind of float
            f.write('\\begin{table}\n')
            caption = self.get_caption()

            if caption is not None:
                f.write("\\caption{%s}" % caption)
            try:
                f.write(r"\label{%s}" % id(self))  # always put in ID
                f.write(r"\label{%s}" % self.attrib[ATTRIB_LABEL])  # put in label if provided

            except KeyError:
                pass  # no caption

            f.write("\n")
            if self.option(OPTION_CENTER):
                f.write('\\begin{center}\n')

        if self.option(OPTION_LONGTABLE):
            f.write('\\begin{longtable}{%s}\n' % self.latex_colspec())
            caption = self.get_caption()

            if caption is not None:
                f.write("\\caption{%s}\n" % caption)
            try:
                f.write("\\label{%s}" % id(self))  # always output myid
                f.write("\\label{%s}" % self.attrib[ATTRIB_LABEL])
            except KeyError:
                pass  # no caption

            f.write("\n")

            for tr in self.findall(f"./{TAG_THEAD}/{TAG_TR}"):
                self.render_latex_table_row(f, tr)

            f.write('\\hline\\endfirsthead\n')
            f.write('\\multicolumn{%d}{c}{(Table \\ref{%s} continued)}\\\\\n' % (self.max_cols(), id(self)))
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
                self.render_latex_table_row(f, tr)

    def render_latex_table_body(self, f):
        """Render the rows that were not added with add_head() command"""
        for tr in self.findall("./TBODY/TR"):
            self.render_latex_table_row(f, tr)

    def render_latex_table_foot(self, f):
        for tr in self.findall("./TFOOT/TR"):
            self.render_latex_table_row(f, tr)
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

    def set_caption(self, caption):
        #  TODO: Validate that this is first
        """The <caption> tag must be inserted immediately after the <table> tag.
        https://www.w3schools.com/tags/tag_caption.asp
        """
        self.add_tag_text(TAG_CAPTION, caption, position=0)

    def set_fontsize(self, size):
        self.attrib[ATTRIB_FONT_SIZE] = str(size)

    def set_latex_colspec(self, latex_colspec):
        """LaTeX colspec is just used when typesetting with latex. If one is
        not set, it auto-generated"""

        self.attrib[ATTRIB_LATEX_COLSPEC] = latex_colspec

    def latex_colspec(self):
        """Use the user-supplied LATEX COLSPEC; otherwise figure one out"""
        try:
            return self.attrib[ATTRIB_LATEX_COLSPEC]
        except KeyError as c:
            return "l" * self.max_cols()

    #################################################################
    # Cell Formatting Routines

    def format_cell(self, cell):
        """Modify cell by setting its text to be its format. Uses eval, so it's not safe."""
        try:
            typename = cell.attrib[ATTR_TYPE]
            typeval  = urllib.parse.unquote(cell.attrib[ATTR_VAL])
        except KeyError:
            return cell

        TYPECONV = {'float': float,
                    'float32': float,
                    'float64': float,
                    'int': int,
                    'int32': int,
                    'int64': int,
                    'str': str}

        try:
            value = TYPECONV[typename](typeval)
        except KeyError as e:
            return str(typeval)

        if isinstance(value, ET.Element):
            value = value.text

        try:
            if cell.attrib[ATTR_TYPE] in INTEGER_TYPES:
                cell.text = self.attrib[ATTRIB_INTEGER_FORMAT].format(int(value))
                return cell
            elif cell.attrib[ATTR_TYPE] in FLOAT_TYPES:
                cell.text = self.attrib[ATTRIB_FLOAT_FORMAT].format(float(value))
                return cell
            elif cell.attrib[ATTR_TYPE] == 'str':
                cell.text = self.attrib[ATTRIB_TEXT_FORMAT].format(value)
                return cell
            else:
                raise ValueError("Unknown cell type: {}".format(cell.attrib[ATTR_TYPE]))
        except TypeError as e:
            raise TypeError(f"TypeError in value: {value} cell: {cell}")
        except AttributeError as e:
            print("cell:", cell)
            raise e
        except ValueError as e:
            pass

        cell.text = self.attrib[ATTRIB_TEXT_FORMAT].format(value)
        return cell

    #################################################################
    # Table Manipulation Routines

    def add_row(self, where, cells, row_attrib={}, row_auto_id=None):
        """
        Add a row of cells to the table.
        You probably want to call add_head(), add_data() or add_foot().

        @param where      - must be TAG_THEAD, TAG_TBODY or TAG_TFOOT
        @param cells      - a list of cells that are added. These are typically Elements made with make_cells()
                            Each will have its id= attribute set if row_auto_id and self.col_auto_ids are set.
        @param row_attrib - the attribute for the row
        """

        # Mutable default value for row_attrib is ok, since we're not changing attrib here or in any subclasses

        assert where in (TAG_THEAD, TAG_TBODY, TAG_TFOOT)

        where_node = self.findall(f".//{where}")[0]

        if row_auto_id is not None:
            row_attrib = {**row_attrib, **{'id': row_auto_id}}

            if self.col_auto_ids is not None:
                for (cell, name) in zip(cells, self.col_auto_ids):
                    cell.attrib['id'] = row_auto_id + "_" + name
            else:
                for (cell, i) in zip(cells, range(len(cells))):
                    cell.attrib['id'] = row_auto_id + "_" + str(i)

        row = ET.SubElement(where_node, TAG_TR, attrib=row_attrib)

        for cell in cells:
            assert isinstance(cell, ET.Element)
            row.append(cell)
            # If cell has COLSPAN>1, then put in placeholder cells that will not render
            try:
                for col in range(1, int(cell.attrib[ATTR_COLSPAN])):
                    row.append(ET.Element(TAG_TIGNORE))
            except KeyError as e:
                pass

    def add_row_values(self, where, tags, values, *, cell_attribs=None, row_attrib=None, row_auto_id=None):
        """
        Create a row of cells and add it to the table. This is called by add_head, add_data, or add_foot.

        @param where  - should be TAG_THEAD/TAG_TBODY/TAG_TFOOT
        @param tags   - a single tag, or a list of tags. If it is a tag, all of the cells are that tag.
        @param values - a list of values, one per column.  Each is automatically formatted.
                        However, if a value is a TD or a TH element, we just copy that element and use it.
        @param cell_attribs - a single cell attrib, or a list of attribs.
                              If a single attrib, it is given to all the cells.
        @param row_attrib   - a single attrib for the row, or a list of attribs
        @param row_auto_id  - the id for the row.
                              Cell IDs will be row-col when rendered if row and col auto_id are provied.
        """

        assert where in (TAG_THEAD, TAG_TBODY, TAG_TFOOT)

        if cell_attribs is None:
            cell_attribs = {}

        if row_attrib is None:
            row_attrib = {}

        # If tags is not a list, make it a list
        if not isinstance(tags, list):
            tags = [tags] * len(values)

        if not isinstance(cell_attribs, list):
            cell_attribs = [cell_attribs] * len(values)

        if not (len(tags) == len(values) == len(cell_attribs)):
            raise ValueError(
                "tags ({}) values ({}) and cell_attribs ({}) must all have same length".format(len(tags), len(values), len(cell_attribs)))

        cells = [self.make_cell(t, v, a) for (t, v, a) in zip(tags, values, cell_attribs)]

        self.add_row(where, cells, row_attrib=row_attrib, row_auto_id=row_auto_id)

    def add_head(self, values, row_attrib=None, cell_attribs=None, col_auto_ids=None, row_auto_id="head"):
        if col_auto_ids is not None:
            if self.col_auto_ids is None:
                self.col_auto_ids = col_auto_ids
            else:
                raise RuntimeError("auto_ids may only be specified once")

        self.add_row_values(TAG_THEAD, 'TH', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id=row_auto_id)

    def add_data(self, values, row_attrib=None, cell_attribs=None, row_auto_id=None):
        self.add_row_values(TAG_TBODY, 'TD', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id=row_auto_id)

    def add_foot(self, values, row_attrib=None, cell_attribs=None):
        self.add_row_values(TAG_TFOOT, 'TD', values, row_attrib=row_attrib, cell_attribs=cell_attribs,
                            row_auto_id="foot")

    def add_data_array(self, rows):
        for row in rows:
            self.add_data(row)

    def make_cell(self, tag, value, attrib):
        """Given a tag, value and attributes, return a cell formatted with the default format.
        If value is a scalar, make and format it. If it is an element, then just make it the children.
        This is called by add_row.
        Note - if value is a ET.Element that is either a TAG_TD or TAG_TH, it will be copied and used, otherwise
               it will be put inside a newly-created TAG_TD or TAG_TH.
        """

        #logging.warning("make_cell(tag=%s,value=%s,attrib=%s)", tag,value,attrib)
        #logging.warning("same: %s",isinstance(value, ET.Element))

        if isinstance(value, ET.Element):
            if value.tag.upper() in [TAG_TH, TAG_TD]:
                cell = copy.copy(value)
                for (k, v) in attrib:
                    cell.attrib[k] = v
            else:
                cell = ET.Element(tag, attrib)
                cell.insert(0, value)
            return cell

        cell = ET.Element(tag, {**attrib,
                                ATTR_VAL: urllib.parse.quote(str(value)),
                                ATTR_TYPE: str(type(value).__name__)})
        self.format_cell(cell)
        return cell

    ################################################################
    # Table get information routines

    def get_caption(self):
        """Return the <caption> tag text"""
        try:
            c = self.findall(".//CAPTION")
            return c[0].text
        except (KeyError, IndexError) as e:
            return None

    def rows(self):
        """Return the rows"""
        return self.findall(".//TR")

    def row(self, n):
        """Return the nth row; n starts at 0"""
        return self.rows()[n]

    def max_cols(self):
        """Return the number of maximum number of cols in the data. Expensive to calculate"""
        return max(len(row.findall("*")) for row in self.rows())

    def get_cell(self, row, col):
        """Return the cell at row, col; both start at 0"""
        return self.cells_in_row(self.row(row))[col]

    def col(self, n):
        """Returns all the cells in column n"""
        return [row[n] for row in self.rows()]


################################################################
##
# covers for making it easy to construct HTML
##
################################################################

# Add some covers for popular paragraph types
def p(*text, **kwargs):
    """Return a paragraph. Text runs are combined"""
    return tydoc().p(*text, **kwargs)


def h1(*text, **kwargs):
    """Return a header 1"""
    return tydoc().h1(*text, **kwargs)


def h2(*text, **kwargs):
    """Return a header 2"""
    return tydoc().h2(*text, **kwargs)


def h3(*text, **kwargs):
    """Return a header 3"""
    return tydoc().h3(*text, **kwargs)


def pre(*text, **kwargs):
    """Return preformatted text"""
    return tydoc().pre(*text, **kwargs)


def b(*text, **kwargs):
    """Return a bold run"""
    return tydoc().b(*text, **kwargs)


def a(*text, href=None, attrib={}, **kwargs):
    """Return an anchor"""
    attrib = copy.copy(attrib)
    if href:
        attrib['href'] = href
    return TyTag().a(*text, attrib=attrib, **kwargs)

def i(text):
    """Return an itallic run """
    e = ET.Element(TAG_I)
    e.text = text
    return e

def th(*text, attrib={}, **kwargs):
    """Return an th element """
    attrib = copy.copy(attrib)
    return TyTag().th(*text, attrib=attrib, **kwargs)

def td(text):
    """Return an td element """
    e = ET.Element(TAG_TD)
    e.text = text
    return e

def showcase(doc):
    print("---DOM---")
    print(ET.tostring(doc, encoding='unicode'))
    print("\n---HTML---")
    doc.render(sys.stdout, format='html')
    print("\n---LATEX---")
    doc.render(sys.stdout, format='latex')
    print("\n---MD---")
    doc.render(sys.stdout, format='md')
    print("\n==========")


def demo1():
    # Verify that render works
    doc = ET.fromstring("<html><p>First Paragraph</p><p>Second <b>bold</b> Paragraph</p></html>")
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
    doc.p("Second ", b, " Paragraph")
    return doc


def demo4():
    doc = tydoc()
    doc.p("First Paragraph")
    doc.p("Second ", b('bold'), " Paragraph")
    return doc


def tabdemo1():
    doc = tydoc()
    doc.title("Test Document")
    doc.h1("Table demo")

    lcr = [{}, {ATTRIB_ALIGN: ALIGN_CENTER}, {ATTRIB_ALIGN: ALIGN_RIGHT}]
    lcrr = lcr + [{ATTRIB_ALIGN: ALIGN_RIGHT}, {ATTRIB_ALIGN: ALIGN_RIGHT}]

    d2 = doc.table()
    d2.set_option(OPTION_TABLE)
    d2.add_head(['State', 'Abbreviation', 'Rank', 'Population', '% Change'])
    d2.add_data(['California', 'CA', 1, 37252895, 10.0], cell_attribs=lcrr)
    d2.add_data(['Virginia', 'VA', 12, 8001045, 13.0], cell_attribs=lcrr)

    doc.p("")
    d2 = doc.table()
    d2.set_option(OPTION_LONGTABLE)
    d2.add_head(['State', 'Abbreviation', 'Population'], cell_attribs={ATTRIB_ALIGN: ALIGN_CENTER})
    d2.add_data(['Virginia', 'VA', 8001045], cell_attribs=lcr)
    d2.add_data(['California', 'CA', 37252895], cell_attribs=lcr)
    return doc


def demo_toc():
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
    doc.insert_toc()
    return doc


#
# Useful for jupyter
#
def jupyter_display_table(val, float_format="{:.5f}"):
    import io
    from IPython.core.display import HTML
    doc = tytable()
    doc.attrib[ATTRIB_FLOAT_FORMAT] = float_format
    if isinstance(val, dict):
        doc.add_head(val.keys())
        for row in zip(*val.values()):
            doc.add_data(row)
    elif isinstance(val, list):
        for row in val:
            doc.add_data(row)
    else:
        raise ValueError(f"not sure how to render '{val}'")

    buf = io.StringIO()
    doc.render(buf, 'html')
    buf.seek(0)
    HTML(buf.read())


if __name__ == "__main__":
    # Showcase different ways of making a document and render it each
    # way:
    if False:
        showcase(demo1())
        showcase(demo2())
        showcase(demo3())
        showcase(demo4())
        showcase(tabdemo1())
    demo_doc = demo_toc()
    print(demo_doc.prettyprint())
    print("add another TOC")
    demo_doc.insert_toc()
    demo_doc.insert_toc()
    demo_doc.insert_toc()
    print(demo_doc.prettyprint())
    exit(0)
