#
# Tools for representing a database schema
#
# Developed by Simson Garfinkel at the US Census Bureau
# 
# Classes:
#   Range     - Describes a range that a value can have, from a to be inclusive. Includes a description of the range
#   Variable - An individual variable. Can have multiple ranges and possible values, as well as type
#   Table    - A set of Variables, and additional metadata
#   Recode   - A recode from one table to another
#   Schema   - A set of Tables and recodes

### NOTE: requires ctools, which must be in your PYTHONPATH

import os
import re
import numpy
import logging
import random
import json
import decimal
from collections import OrderedDict

unquote_re     = re.compile("[\u0022\u0027\u2018\u201c](.*)[\u0022\u0027\u2019\u201d]")
type_width_re  = re.compile(r"([A-Z0-9]+)\s*[(](\d+)[)]") # matches a type and width specification
note_re        = re.compile(r"Note([ 0-9])*:",re.I)
assignVal_re   = re.compile(r"([^=]*)\s*=\s*(.*)")
assignRange_re = re.compile(r"(.*)\s*[\-\u2013\u2014]\s*([^=]*)(=\s*(.*))?")
range_re       = re.compile(r"(\S*)\s*[\-\u2013\u2014]\s*(\S*)") # handles unicode dashes
integer_re     = re.compile(r"INTEGER ?\((\d+)\)",re.I)

TYPE_NUMBER    = "NUMBER"
TYPE_INTEGER   = "INTEGER"
TYPE_INT       = "INT"
TYPE_VARCHAR   = "VARCHAR"
TYPE_CHAR      = "CHAR"
TYPE_DECIMAL   = "DECIMAL"
TYPE_FLOAT     = "FLOAT"
TYPE_DATE      = "DATE"
TYPE_SDO_GEOMETRY = "SDO_GEOMETRY"
TYPE_STRING = "STRING"
# map SQL names to Python types
PYTHON_TYPE_MAP= {TYPE_NUMBER:int,
                  TYPE_INTEGER:int,
                  TYPE_INT:int,
                  TYPE_VARCHAR:str,
                  TYPE_CHAR:str,
                  TYPE_FLOAT:float,
                  TYPE_DATE:str,
                  TYPE_SDO_GEOMETRY:str,
                  TYPE_STRING:str,
                  TYPE_DECIMAL:decimal.Decimal }
# Python types to SQL names
SQL_TYPE_MAP = { int: {'type': TYPE_INTEGER,'width':8},
                 str: {'type': TYPE_VARCHAR,'width':254},
                 float: {'type': TYPE_FLOAT,'width': 15},
                 decimal.Decimal: {'type': TYPE_DECIMAL, 'width':15}}
    

DEFAULT_VARIABLE_WIDTH = 8
WIDTH_MAX       = 255

SAS7BDAT_EXT   = ".sas7bdat"
CSV_EXT        = ".csv"
TXT_EXT        = ".txt"
PANDAS_EXTS    = set([SAS7BDAT_EXT,CSV_EXT,TXT_EXT])
PANDAS_CHUNKSIZE = 1000

# Special ranges
RANGE_NULL = "NULL"           # if NULL, then interpret as the empty string
RANGE_ANY  = "N/A"            # if N/A, allow any

SQLITE3 = 'sqlite3'
MYSQL = 'mysql'
SQL_SCHEMA = {MYSQL : {'param':'%s'},
              SQLITE3 : {'param':'?'}
              }

# Included in programmatically-generated output
SCHEMA_SUPPORT_FUNCTIONS="""
def leftpad(x,width):
    return ' '*(width-len(str(x)))+str(x)

def between(a,b,c,width):
    if len(b) > width:
        return False
    if '.' in a or '.' in b or '.' in c:
        try:
            return float(leftpad(a,width)) <= float(leftpad(b,width)) <= float(leftpad(c,width))
        except:
            pass  # tries to return a float but might have weird input like 1.1.0 which will be compared traditionally instead
    return leftpad(a,width) <= leftpad(b,width) <= leftpad(c,width)


def safe_int(i):
    try:
        return int(i)
    except (TypeError, ValueError) as e:
        return None

def safe_float(i):
    try:
        return float(i)
    except (TypeError, ValueError) as e:
        return None

def safe_str(i):
    try:
        return str(i)
    except (TypeError, ValueError) as e:
        return None
"""

def valid_sql_name(name):
    for ch in name:
        if ch.isalnum()==False and ch not in ['_']:
            return False
    return True

def decode_vtype(t):
    """Given VARCHAR(2) or VARCHAR or VARCHAR2(2) or INTEGER(2), return the type and width"""
    if t==None:
        return (None,None)
    t = t.upper().replace("VARCHAR2","VARCHAR")
    m = type_width_re.search(t)
    if m:
        vtype = m.group(1)
        width = int(m.group(2))
    else:
        vtype = t
        width = DEFAULT_VARIABLE_WIDTH
    if vtype not in PYTHON_TYPE_MAP:
        raise ValueError("vtype {} is not in PYTHON_TYPE_MAP".format(vtype))
    return (vtype,width)
    

def vtype_for_numpy_type(t):
    try:
        return {bytes:TYPE_CHAR,
                float:TYPE_NUMBER,
                numpy.float64:TYPE_NUMBER,
                str:TYPE_CHAR,
                int:TYPE_NUMBER,
                }[t]
    except KeyError as e:
        logging.error("Unknown type: {}".format(t))
        raise e

def sql_type_for_python_value(val):
    stm = SQL_TYPE_MAP[type(val)]
    return f"{stm['type']}({stm['width']})"

def unquote(s):
    m = unquote_re.match(s)
    if m:
        return m.group(1)
    else:
        return s


#
# Simson's cut-rate SQL parser
#
create_re = re.compile(r'CREATE TABLE (\S*) \(( .* )\)',re.I)
var_re    = re.compile(r'(\S+) (\S+)')

SQL_TABLE = 'table'
SQL_COLUMNS = 'cols'

def sql_parse_create(stmt):
    if "--" in stmt:
        raise RuntimeError("Currently cannot handle comments in SQL")
    ret = {}
    ret[SQL_TABLE] = None
    ret[SQL_COLUMNS]  = []
    
    # make all spaces a single space
    stmt = re.sub(r"\s+"," ",stmt).strip()

    m = create_re.search(stmt)
    if m:
        ret[SQL_TABLE] = m.group(1)
        for vdef in m.group(2).split(","):
            vdef = vdef.strip()
            m = var_re.search(vdef)
            (vtype,name) = m.group(1,2)
            ret[SQL_COLUMNS].append({'vtype':vtype, 'name':name})
    return ret




def clean_int(s):
    """ Clean an integer """
    while len(s)>0:
        if s[0]==' ':
            s=s[1:]
            continue
        if s[-1] in " ,":
            s=s[0:-1]
            continue
        break
    return int(s)


def convertValue(val, vtype=None):
    """Make the value better"""
    try:
        if vtype not in [TYPE_VARCHAR,TYPE_CHAR]:
            return clean_int(val)
    except ValueError:
        pass
    val = val.strip()
    if val.lower()=="null" or val=="EMPTY-STRING":
        val = ""
    return val


DEFAULT_VARIABLE_FORMAT = '{}'


