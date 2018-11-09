#!/usr/bin/env python3
#
"""
hiearchical_configparser.py:

Like a regular configparser, but supports the INCLUDE= statement.
If INCLUDE=filename.ini is present in any section, the contents of that section are
read from filename.ini. If filename.ini includes its own INCLUDE=, that is included as well.

Name/value pairs in the included file are read FIRST, so that they can be shadowed by name/value
pairs in the including file. 

If the INCLUDE= is when the [DEFAULT] section, then the values of *every* section are incluced.
"""

from configparser import ConfigParser
from copy import copy

DEFAULT='default'
INCLUDE='include'

class HiearchicalConfigParser(ConfigParser):
    def read(self,filename,read_files=set()):
        """First read the requested filename into a temporary config parser.
        Scan for any INCLUDE statements.If any are found in any section, read the included file 
        recursively, unless it has already been read.
        """
        cf = ConfigParser()
        cf.read(filename)

        #print(filename,"BUILDING CONFIG STRUCTURE FOR FILE")
        sections = set(cf.sections())
        read_files_default = copy(read_files)
        # If there is an INCLUDE in the default section, see if the included file
        # specifies any sections that we did not have. If there is, get those sections too
        default_include_file = None
        if DEFAULT in cf:
            if INCLUDE in cf[DEFAULT]:
                default_include_file = cf[DEFAULT][INCLUDE]
                if default_include_file not in read_files_default:
                    read_files_default.add(default_include_file)
                    #print(filename,"READING STRUCTURE FROM DEFAULT INCLUDE FILE",default_include_file)
                    cp = HiearchicalConfigParser()
                    cp.read(default_include_file, read_files=read_files_default)
                    for section in cp.sections():
                        if section not in sections:
                            sections.add(section)

        # Now, for each section from the file we were supposed to read combined with the sections
        # specified in the default include file, see if there are any include files.
        # Note that there may potentially be two include files: one from the section, and one from
        # the default. We therefore read the default include file first, if it exists, and copy those
        # options over. Then we read the ones in the include if, if there is any, and copy those options over.
        # print(filename,"READING INCLUDE FILES FOR FILE")
        for section in sections:
            # make a local copy of the files we read for this section
            section_include_files_read = copy(read_files) 

            # If this section is not in self or cf, add it. (We must have gotten in from the default)
            if section not in self:
                self.add_section(section)
            if section not in cf:
                cf.add_section(section)

            section_include_file = cf[section].get(INCLUDE,None)
            for include_file in [default_include_file, section_include_file]:
                #print(filename,"SECTION=",section,"INCLUDE_FILE=",include_file)
                if include_file and (include_file not in section_include_files_read):
                    section_include_files_read.add(include_file) # note that we have read it
                    #print(filename,"READING ",include_file,'for section',section)
                    cp = HiearchicalConfigParser()
                    cp.read(include_file, read_files=section_include_files_read)
                    #print(filename,"CP has been read. Here it is:")
                    #cp.write(open('/dev/stdout','w'))
                    if section in cp:
                        #print(filename,"++++++++  now copy out the keys in section",section)
                        for option in cp[section]:
                            self.set(section,option, cp[section][option])
                            #print(filename,"set ",section,option,cp[section][option])
                    #else:
                    #   print(filename,"++++++++  no section",section)

            # Now, copy over all of the options for this section in the file that we were 
            # actually asked to read, rather than the include file
            #print(filename,"COPYING OVER OPTIONS FROM",filename,"FOR SECTION",section)
            for option in cf[section]:
                self.set(section,option, cf[section][option])
                #print(filename,"set2 ",section,option,cf[section][option])

        # All done
        #print(filename,"Current file:")
        #self.write(open("/dev/stdout","w"))
        #print(filename,"----------------")

    def read_string(self,string,source=None):
        raise RuntimeError("read_string not implemented")

    
