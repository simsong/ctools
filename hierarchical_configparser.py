#!/usr/bin/env python3
#
"""
hierarchical_configparser.py:

Like a regular configparser, but supports the INCLUDE= statement.
If INCLUDE=filename.ini is present in any section, the contents of that section are
read from filename.ini. If filename.ini includes its own INCLUDE=, that is included as well.

Name/value pairs in the included file are read FIRST, so that they can be shadowed by name/value
pairs in the including file. 

If the INCLUDE= is when the [DEFAULT] section, then the values of *every* section are included.

Don't have INCLUDE loops. I tried to protect against them, but it was too hard.
"""

import os
import os.path
import logging
import sys
from configparser import ConfigParser
from copy import copy
from collections import defaultdict 

DEFAULT='default'
INCLUDE='include'

def fixpath(base,name):
    """If name is not an absolute path name, make it relative to the directory of base"""
    if name[0]=='/': 
        return name
    return os.path.join(os.path.dirname(base), name)

def sectionsInConfigFile(filename):
    """Given a config file, return a set of all the sections it contains"""
    cf = HierarchicalConfigParser()
    cf.read(filename)
    return set(cf.sections())

class HierarchicalConfigParser(ConfigParser):
    cache = dict()              # maps filenames to a dictionary
    def __init__(self, *args, debug=False, **kwargs):
        super().__init__(*args,  **kwargs)
        self.debug       = debug
        self.seen_files  = set()
        self.source      = defaultdict(dict) # maps source[section][option] to filename

    def explain(self,out):
        print("# Explaining open file",file=out)
        print("# format:  filename:option = value",file=out)
        for section in self.source:
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
            for section in co.sections():
                if section not in self:
                    self.add_section(section)
                for option in co[section]:
                    self[section][option] = co[section][option]
            return

        # Read with the normal config file machinery, except require that filename exist.
        # and track that we read the file
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)
        super().read(filename)
        self.seen_files.add(filename)

        if self.debug:
            print(filename,"READ SECTIONS:",self.sections(), file=sys.stderr)

        # If there is an INCLUDE in the default section, see if the included file
        # specifies any sections that we did not have. If there is, create a section that the options will be included.

        if (DEFAULT in self) and (INCLUDE in self[DEFAULT]):
            include_file = self[DEFAULT][INCLUDE]
            if self.debug:
                print(filename,f"{filename} [DEFAULT] INCLUDE={include_file}",file=sys.stderr)
            for section in sectionsInConfigFile( fixpath( filename, include_file )):
                if section not in self:
                    if self.debug:
                        print(filename,f"{filename} Adding section {section}",file=sys.stderr)
                    self.add_section(section)
                        
        # For each section see if there is an INCLUDE. Get the file and set the options not already set.

        for section in self.sections():
            if self.debug:
                print(filename,"PROCESSING SECTION",section, file=sys.stderr)
            if (INCLUDE in self[section]) or ((DEFAULT in self) and (INCLUDE in self[DEFAULT])):
                try:
                    section_include_file = self[section][INCLUDE]
                except KeyError:
                    section_include_file = self[DEFAULT][INCLUDE]
                section_include_file = fixpath(filename, section_include_file)
                if not os.path.exists(section_include_file):
                    raise FileNotFoundError("File {} [{}]  INCLUDE={} not found".format(filename, section, section_include_file))
                if self.debug:
                    print(filename,"READING SECTION",section,"FROM",section_include_file, file=sys.stderr)
                cp = HierarchicalConfigParser(debug=self.debug)
                cp.read( section_include_file )
                if section in cp.sections():
                    for option in cp.options(section):
                        if option not in self.options(section):
                            self.set(section, option, cp[section][option] )
                            self.source[section][option] = section_include_file
                self.seen_files.add( section_include_file )

        # Store results in the cache
        HierarchicalConfigParser.cache[filename] = self

        # All done
        if self.debug:
            print(filename,"RETURNING:",file=sys.stderr)
            self.write(open("/dev/stderr","w"))
            print(filename,"============")

    def read_string(self,string,source=None):
        raise RuntimeError("read_string not implemented")

    
