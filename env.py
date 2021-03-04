"""manage the census environment"""


import os
import re
import pwd
import sys
import glob

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



def get_env(pathname=None, *, profile_dir=None, prefix=None):
    """Read the BASH file and extract the variables. Currently this is
done with pattern matching. Another way would be to run the BASH
script as a subshell and then do a printenv and actually capture the
variables
    :param pathname: if provided, use this path
    :param profile_dir: If provided, search this directory
    :param prefix: if provided and profile_dir is provided, search for all files in the directory
    :return: the variables that were learned.
"""
    if (pathname is not None) and (profile_dir is not None):
        raise ValueError("pathname and profile_dir canot both be provided")
    if (profile_dir is not None) and (prefix is None):
        raise ValueError("If profile_dir is provided, pathname must be provided.")
    if profile_dir:
        names = sorted(glob.glob(os.path.join(profile_dir, prefix+"*")))
        if len(names)==0:
            raise FileNotFoundError(f"No file with prefix {prefix} in {profile_dir}")
        pathname = names[0]

    ret = {}
    for (key,val) in get_vars(pathname).items():
        ret[key] = os.environ[key] = os.path.expandvars(val)
    return ret


def get_census_env():
    """Legacy to be deleted"""
    return get_env(profile_dir = '/etc/profile.d', prefix = 'census')

def get_home():
    """Return the current user's home directory without using the HOME variable. """
    return pwd.getpwuid(os.getuid()).pw_dir


def dump(out):
    print("==== ENV ====",file=out)
    for (key,val) in os.environ.items():
        print(f"{key}={val}",file=out)
