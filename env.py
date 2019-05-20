"""manage the census environment"""


import os
import re

CENSUS_DAS_SH='/etc/profile.d/census_das.sh'
EXPORT_RE = re.compile("^export ([a-zA-Z][a-zA-Z0-9_]*)=(.*)$")

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
        
