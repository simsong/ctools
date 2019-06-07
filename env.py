"""manage the census environment"""


import os
import re

CENSUS_DAS_SH='/etc/profile.d/census_das.sh'
VARS_RE   = re.compile(r"^(export)?\s*([a-zA-Z][a-zA-Z0-9_]*)=(.*)$")
EXPORT_RE = re.compile(r"^export ([a-zA-Z][a-zA-Z0-9_]*)=(.*)$")

def get_vars(fname):
    """Read the variables in fname and return them in a dictionary"""
    ret = {}
    with open(fname,'r') as f:
        for line in f:
            m = VARS_RE.search(line)
            if m:
                ret[m.group(1)] = m.group(2)
    return ret
                



def get_census_env():
    """Read the file /etc/profile.d/census_das.sh and learn all of the environment variables"""
    with open(CENSUS_DAS_SH,'r') as f:
        for line in f:
            m = EXPORT_RE.search(line)
            if m:
                key = m.group(1)
                val = m.group(2)
                if val[0] in ('"',"'") and val[0]==val[-1]:
                    val = val[1:-1]
                os.environ[key] = os.path.expandvars(val)
        
