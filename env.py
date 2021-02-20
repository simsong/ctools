"""
env.py:

Read a bash script and learn the environment variables into a python dictionary.
This allows MySQL database host, database, username and password to be set in
environment variables for both bash scripts and Python programs.

Todo: remove CENSUS_DAS_SH or find it.
"""

import os
import re
import pwd
import sys

CENSUS_DAS_SH='/etc/profile.d/census_das.sh'
VARS_RE   = re.compile(r"^(export)?\s*(?P<name>[a-zA-Z][a-zA-Z0-9_]*)=(?P<value>.*)$")
EXPORT_RE = re.compile(r"^export ([a-zA-Z][a-zA-Z0-9_]*)=(.*)$")

def get_vars(fname):
    """Read the variables in fname and return them in a dictionary"""
    ret = {}
    with open(fname,'r') as f:
        for line in f:
            m = VARS_RE.search(line)
            if m:
                name  = m.group('name')
                value = m.group('value')
                if (len(value)>0) and (value[0] in ['"',"'"]) and (value[0]==value[-1]):
                    value = value[1:-1]
                ret[name] = value
    return ret


def get_env(pathname):
    """Read the BASH file and extract the variables. Currently this is
done with pattern matching. Another way would be to run the BASH
script as a subshell and then do a printenv and actually capture the
variables"""
    for (key,val) in get_vars(pathname).items():
        os.environ[key] = os.path.expandvars(val)


def get_census_env():
    """Read the file /etc/profile.d/census_das.sh and learn all of the
environment variables"""
    get_env(CENSUS_DAS_SH)

def get_home():
    """Return the current user's home directory without using the HOME variable. """
    return pwd.getpwuid(os.getuid()).pw_dir

def dump(out):
    print("==== ENV ====",file=out)
    for (key,val) in os.environ.items():
        print(f"{key}={val}",file=out)

if __name__=="__main__":
    """Read a file and print the learned variables"""
    import argparse
    parser = argparse.ArgumentParser(description='Import the Digital Corpora logs.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("envfile",help="File with environment variables set by bash")
    args = parser.parse_args()

    d = get_vars(args.envfile)
    for (k,v) in d.items():
        print(f"{k}={v}")
