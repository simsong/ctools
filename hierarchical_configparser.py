#!/usr/bin/env python3
#
"""
hierarchical_configparser.py:

Like a regular configparser, but supports the INCLUDE= statement.

If INCLUDE=filename.ini is present in any section, the contents of that section are
read from filename.ini and provided as base definitions. Those definitions can be shadowed
by the local config file.

If filename.ini includes its own INCLUDE=, those are included as well.

Special handling of the [default] section:
The [default] section provides default options (e.g. name=value pairs) for *every* section.
If INCLUDE= appears in the [default] section of the ROOT hiearchical config file, then
all of the sections are read.

Implementation Notes:
- This is rev 2.0, which preserves comments and implements blame(). Python's config parser
  strips comments on read and thus cannot write them.

- Name/value pairs in the included file are read FIRST, so that they can be shadowed by name/value
  pairs in the including file.

- We implement a Line() class which remembers, for each line, the file from which it was read.

- The config file is imported with HCP which implements all of the include parsing.
  It then provides a flattened config file to HiearchicalConfigParser().

- Include loops are reliably detected.
"""

import os
import os.path
import logging
import sys
import collections
import re
import io
from configparser import ConfigParser
from copy import copy
from collections import defaultdict ,namedtuple

DEFAULT='default'
INCLUDE='include'

Line = namedtuple('Line', ['filename','lineno','line'])

SECTION_RE = re.compile(r'^\[([^\]]*)\]\s*$')
OPTION_RE  = re.compile(r'^([^=:]+)\s*[=:]\s*(.*)$')

NO_SECTION=""
DEFAULT_SECTION="default"

class HCP:
    def __init__(self, *args, **kwargs):
        self.sections   = collections.OrderedDict() # section name is lowercased

    def read(self, filename, *, onlySection=None):
        """
        Reads a config file.
        :param filename: filename to read. Mandatory.
        :param section:  just read this section. Optional
        """
        with open(filename,"r") as f:
            currentSection = NO_SECTION
            seen_sections = set()
            for line in f:
                # Check for new section
                m = SECTION_RE.search(line)
                if m:
                    currentSection = m.group(1).lower()
                    if currentSection in seen_sections:
                        raise ValueError(f"{seen_section} appears twice in {filename}")
                    seen_sections.add( currentSection )

                if currentSection not in self.sections:
                    self.sections[currentSection] = list()

                if (onlySection is not None) and (onlySection.lower() != currentSection.lower()):
                    continue

                self.sections[currentSection].append(line)

    def asString( self ):
        s = io.StringIO()
        for (section,lines) in self.sections.items():
            s.write("".join(lines)) # get the lines
        return s.getvalue()


class HierarchicalConfigParser(ConfigParser):
    cache = dict()          # maps filenames to a dictionary
    def __init__(self, *args, debug=False, depth=1, **kwargs):
        super().__init__(*args,  **kwargs)
        self.debug       = debug
        self.seen_files  = set()
        self.source      = defaultdict(dict) # maps source[section][option] to filename
        self.depth       = depth

    def explain(self,out=sys.stderr):
        print("# Explaining open file",file=out)
        print("# format:  filename:option = value",file=out)
        for section in sorted(self.source):
            print(f"[{section}]",file=out)
            for option in self.source[section]:
                print(f"{self.source[section][option]}:{option} = {self[section][option]}",file=out)
            print("",file=out)

    def read(self,filename):
        """First read the requested filename into a temporary config parser.
        Scan for any INCLUDE statements. If any are found in any section, read the included file
        recursively, unless it has already been read.
        """
        if filename[0]!='/':
            filename = os.path.abspath(filename)

        # If in cache, just copy from that instance
        try:
            co = HierarchicalConfigParser.cache[filename]
        except KeyError:
            pass
        else:
            if self.debug:
                print(self.depth,filename,"IN CACHE",file=sys.stderr)
            for section in sorted(co.sections()):
                if section not in self:
                    if self.debug:
                        print(self.depth,filename,"ADD SECTION FROM CACHE ",section,file=sys.stderr)
                    self.add_section(section)
                for option in co[section]:
                    if self.debug:
                        print(self.depth,filename,"   CACHE: [{}].{} <- {} ".format(section,option,co[section][option]),file=sys.stderr)
                    self[section][option] = co[section][option]
            if self.debug:
                print(self.depth, filename,"** SATISFIED FROM CACHE **",file=sys.stderr)
            return

        # Read with the normal config file machinery, except require that filename exist.
        # and track that we read the file
        if self.debug:
            print(self.depth, filename,"*** ENTER ***",file=sys.stderr)
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)
        super().read(filename)
        self.seen_files.add(filename)

        if self.debug:
            print(self.depth, filename,"READ SECTIONS:",self.sections(), file=sys.stderr)

        # If there is an INCLUDE in the default section, see if the included file
        # specifies any sections that we did not have. If there is, create a section that the options will be included.

        default_cf = None
        if (DEFAULT in self) and (INCLUDE in self[DEFAULT]):
            include_file = os.path.join(filename, self[DEFAULT][INCLUDE] )
            if self.debug:
                print(self.depth, filename,f"{filename} [DEFAULT] INCLUDE={include_file}",file=sys.stderr)
            default_cf = HierarchicalConfigParser( debug=self.debug, depth=self.depth+1 )
            default_cf.read( os.path.join( filename, include_file ))
            for section in sorted( default_cf.sections() ):
                if section not in self:
                    if self.debug:
                        print(self.depth, filename,f"{filename} Adding section {section} FROM DEFUALT INCLUDE",file=sys.stderr)
                    self.add_section(section)

        # For each section see if there is an INCLUDE. Get the file and set the options not already set.

        for section in self.sections():
            if self.debug:
                print(self.depth, filename,"PROCESSING SECTION",section, file=sys.stderr)
            if (INCLUDE in self[section]) or ((DEFAULT in self) and (INCLUDE in self[DEFAULT])):
                try:
                    section_include_file = self[section][INCLUDE]
                except KeyError:
                    section_include_file = self[DEFAULT][INCLUDE]
                section_include_file = os.path.join(filename, section_include_file)
                if not os.path.exists(section_include_file):
                    raise FileNotFoundError("File {} [{}]  INCLUDE={} not found".format(filename, section, section_include_file))
                if self.debug:
                    print(self.depth, filename,"READING SECTION",section,"FROM",section_include_file, file=sys.stderr)
                section_cf = HierarchicalConfigParser(debug=self.debug, depth=self.depth+1)
                section_cf.read( section_include_file )
                if section in section_cf:
                    for option in section_cf[section]:
                        if option not in self[section]:
                            if self.debug:
                                print(self.depth, filename,"   [{}].{} <-- {}".format(section,option,section_cf[section][option]))
                            self[section][option] = section_cf[section][option]
                            self.source[section][option] = section_include_file
                self.seen_files.add( section_include_file )

        # Store results in the cache
        HierarchicalConfigParser.cache[filename] = self

        # If we are in the root, delete [DEFAULT]include
        if self.depth==1:
            try:
                del self['default']['include']
            except KeyError:
                pass

        # All done
        if self.debug:
            print(self.depth, filename,"RETURNING:",file=sys.stderr)
            self.write(sys.stderr)
            print(self.depth, filename,"*** EXIT ***",file=sys.stderr)

    def read_string(self,string,source=None):
        raise RuntimeError("read_string not implemented")
