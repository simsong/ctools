import logging
from os.path import dirname, abspath
import sys
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
#from ctools.schema import *
import ctools.schema as schema
from ctools.schema.range import Range, convertRange
from ctools.schema import valid_sql_name,decode_vtype,SQL_TYPE_MAP

class Variable:
    """The MDF Variable.
    name     = the name of the variable. Must be unique when added to a table.
    vtype    = a string with the SQL type; look at TYPE_* variables at top of file.
    python_type = the python type corresponding to vtype
    desc     = description of variable.
    field    = the field number (first field is field #0) (also the position)
    column   = the starting column (first column is 0)
    width    = the width for column-specified
    ranges   = A set of Range objects that specify valid ranges. If none provided, all ranges are valid.
    default  = default value for this
    format   = when printing, format to use
    prefix   = A prefix that is always provided for the variable and ignored
    attrib   = a dictionary of user-specified attributes
    """

    __slots__ = ('name','python_type','vtype','desc','position','column','width','ranges','default','format','prefix','attrib','allow_whitespace','start','end','allow_null')

    def __init__(self,*,name=None,vtype=None,python_type=None,desc="",position=None,column=None,width=None,default=None,
                 format=schema.DEFAULT_VARIABLE_FORMAT,attrib={},prefix="",allow_whitespace=False,start=None,end=None, allow_null=False):
        self.width       = None       # initial value
        self.set_name(name)
        self.set_vtype(vtype=vtype, python_type=python_type)
        #self.field      = field         # field number
        self.position    = position
        self.desc        = desc          # description
        self.column      = column        # Starting column in the line if this is a column-specified file 0
        self.start = start
        self.end = end
        self.allow_null = allow_null


        # If width was specified, use it
        if width:
            try:
                self.width   = int(width)         # number of characters wide
            except ValueError:
                print(f"No width passed to {self.name}, using default")

        self.ranges      = set()
        self.default     = default
        self.format      = format
        self.prefix      = prefix
        self.attrib      = attrib
        self.allow_whitespace = allow_whitespace

    def __str__(self):
        return "{}({} column:{} width:{})".format(self.name,self.python_type.__name__,self.column,self.width)

    def __repr__(self):
        return "Variable(position:{} name:{} desc:{} vtype:{})".format(self.position,self.name,self.desc,self.vtype)

    def json_dict(self):
        return {"name":self.name,
                "vtype":self.vtype,
                "position":self.position,
                "desc":self.desc,
                "column":self.column,
                "width":self.width,
                "ranges":[range.json_dict() for range in self.ranges] }

    def set_name(self,name):
        self.name = name
        if self.name and not valid_sql_name(name):
            raise RuntimeError("invalid SQL Variable name: {}".format(name)) 

    def set_vtype(self,vtype=None,python_type=None):
        """sets both vtype and python_type. Only one should be provided
        v may be in any type in PYTHON_TYPE_MAP and it may have an optional width specification.
        VARCHAR2 (used by Oracle) is automatically converted to VARCHAR.
        """
        if vtype is not None and python_type is None:
            (self.vtype,self.width) = decode_vtype(vtype)
            assert 1 <= self.width <= schema.WIDTH_MAX
            self.python_type = schema.PYTHON_TYPE_MAP[self.vtype]
            assert self.python_type is not None
        elif vtype is None and python_type is not None:
            self.vtype = SQL_TYPE_MAP[python_type]['type']
            self.width = SQL_TYPE_MAP[python_type]['width']
            self.python_type = python_type
        else:
            self.vtype = None
            self.width = None
            self.python_type = None

    def set_column(self, start:int, end:int):
        """Note the first column is column 0, not column 1.  Data is in start..end inclusive"""
        assert type(start)==int and start>=0
        assert type(end)==int and end>=0
        assert end>=start
        self.column = start
        self.width  = (end-start)+1
        
    def sql_type(self):
        """Return the type as an SQL expression"""
        if self.width:
            return "{}({})".format(self.vtype,self.width)
        return self.vtype
        
    def find_default_from_allowable_range_descriptions(self,text):
        """Search through all of the allowable ranges. If one of them has a
        TEXT in its description, use the first value of the range as
        the default value

        """
        # If there is only one allowable range and there is no range, it's the default
        if len(self.ranges)==1:
            r = next(iter(self.ranges))
            if r.a==r.b:
                self.default = r.a
                return

        # The 'in' operator is the fastest way to do this; see:
        # https://stackoverflow.com/questions/4901523/whats-a-faster-operation-re-match-search-or-str-find
        text = text.lower()
        for r in self.ranges:
            if text in r.desc.lower():
                self.default = r.a
                return

    def add_range(self,newrange):
        """Add a range of legal values for this variable."""
        assert isinstance(newrange,Range)
        if newrange in self.ranges:
            raise RuntimeError("{}: duplicate range: {}".format(self.name,newrange))
        self.ranges.add(newrange)

    def add_valid_data_description(self,desc):
        """Parse the variable descriptions typical of US Census Bureau data
        files that are used to describe valid values."""
        if "\n" in desc:
            for line in desc.split("\n"):
                self.add_valid_data_description(line)
            return
        if "," in desc:
            for line in desc.split(","):
                self.add_valid_data_description(line)
            return
        r = Range.extract_range_and_desc(desc, width=self.width)
        self.ranges.add(r)


    def random_value(self):
        """Generate a random value"""
        if "f" in self.format:   # special case for floating points that specify a range
            r = random.choice(self.ranges)
            val = self.format.format(random.uniform(r[0],r[1]))

        elif self.ranges:
            random_range = random.choice(self.ranges)
            val = random_range.random_value()

        elif self.vtype== schema.TYPE_VARCHAR or self.vtype== schema.TYPE_CHAR: # make a random VCHAR
            width = self.width if self.width else 6
            val = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(width))

        elif self.vtype== schema.TYPE_NUMBER or self.vtype== schema.TYPE_INTEGER: # make a random number
            width = self.width
            val   = random.randint(0,(10**self.width)-1)
        else:
            raise RuntimeError("variable:{} vtype:{} width:{} no allowable values or ranges".format(self.name,self.vtype,self.width))

        if self.prefix:
            val = self.prefix + str(val)

        # Look for "up to nn characters" or "nn characters"
        if type(val)==str:
            if "characters" in val.lower():
                m = re.search(r"(up to)?\s*([0-9]+)\s*characters",val,re.I)
                if not m:
                    raise RuntimeError("Cannot decode: '{}'".format(val))
                val = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(int(m.group(2))))

            # Look for "nn blanks"
            if "blanks" in val.lower():
                m = re.search(r"([0-9]+)\s+blanks",val,re.I)
                if not m:
                    raise RuntimeError("Cannot decode: '{}'".format(val))
                val = " " * int(m.group(1))
        return val

    def python_validator_name(self):
        return "is_valid_" + self.name

    def python_validation_text(self):
        ranges = Range.combine_ranges(self.ranges)
        return ", ".join(['{}-{}'.format(r.a,r.b) for r in ranges])

    def python_validator(self):
        ret = []
        ret.append("    @classmethod")
        ret.append("    def {}(self,x):".format(self.python_validator_name()))
        ret.append('        """{}"""'.format(self.desc))
        if self.allow_null:
            ret.append("        if x is None or x == \"None\":")
            ret.append("            return True")
        else:
            ret.append("        if x is None or x == \"None\":")
            ret.append("            return False")
        if self.allow_whitespace:
            size = "".rjust(self.width, " ")
            ret.append("        if x == '{}':".format(size))
            ret.append("            return True")

        if self.python_type == int or self.python_type == float:
            ret.append('        x = str(x).strip()')
            ret.append('        try:')
            if self.python_type==int:
                ret.append('            x = int(x)')
            if self.python_type==float:
                ret.append('            x = float(x)')
            ret.append('        except ValueError:')
            ret.append('            return False')
        ranges = Range.combine_ranges(self.ranges)
        try:
            expr = " or ".join(["({})".format(r.python_expr(self.python_type, self.width)) for r in ranges])
        except ValueError as e:
            logging.error("Cannot create python range expression for variable "+str(self))
            raise RuntimeError("Cannot create python range expression for variable "+str(self))
            
        if expr=="":
            expr = "True"
        ret.append("        return "+expr)
        return "\n".join(ret)+"\n"

        
    def vformat(self,val):
        """Format a value according to val's type and the variable's type. By default, just pass it through."""
        if type(val)==int and self.vtype== schema.TYPE_CHAR:
            """An integer is being formatted as a fixed with character. Be sure it is 0-filled"""
            return str(val).zfill(self.width)
        if type(val)==str and self.vtype== schema.TYPE_CHAR:
            """An integer is being formatted as a fixed with character. Be sure it is 0-filled"""
            return str(val).rjust(self.width,' ')
        return str(val)

    def dump(self,func=print):
        out = "".join([ "  ",
                        f" #{self.position}" if self.position is not None else "",
                        f"[{self.column}:{self.width}] ",
                        f"{self.name} ",
                        f"({self.desc}) " if self.desc else "",
                        f"{self.vtype}"])
        func( out )

        for r in sorted(self.ranges):
            func(f"      {f}")
        if self.default is not None:
            func(f"      DEFAULT: {self.default}")


