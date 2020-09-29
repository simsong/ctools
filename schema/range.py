import re
import logging
import random

import ctools.schema  as schema
from ctools.schema import clean_int

IN_INTEGER = "integer"
IN_NULL = "null"
IN_ALPHANUMERIC = "alphanumeric"
IN_WHITESPACE = "whitespace"

def all_ints(ranges):
    for r in ranges:
        if r.is_int()==False:
            return False
    return True

def convertRange(a,b, desc=None, vtype=None):
    try:
        if vtype not in [schema.TYPE_VARCHAR, schema.TYPE_CHAR]:
            return Range(clean_int(a),clean_int(b), desc)
    except ValueError:
        pass
    return Range(a.strip(),b.strip(), desc)

class Range:
    """Describe a range that a value can have, from a to b inclusive
    [a,b]
    This is type-free, but we should have kept the type of the variable for which the range was made. 
    """
    RANGE_RE_LIST = [
        re.compile(r"^(?P<a>!+)(?P<desc>.*)"), # used for grabbing vals with ! as that is a legal val
        re.compile(r"^.*(?P<a>\balphanumeric\b)(?P<desc>.*)"), # some descriptions mention alphanumeric vals legal
        re.compile(r"^.*(?P<a>[Ww]hitespace)(?P<desc>.*)"),  # grabs w/Whitespace, and returns none, white handled elsewhere
        re.compile(r"^.*(?P<a>\bnull\b)(?P<desc>.*)"), # if val is null, return None
        re.compile(r"^.*(?P<a>integers?)(?P<desc>.*)"), # some descs just say integer, this catches that
        re.compile(r"^(?P<a>\-?\+?\d+.?\d+) ?to ?(?P<b>\-?\+?\d+.?\d+) ?(?P<desc>.*)"), # catch ranges built like 1 to 3
        re.compile(r"^(?P<a>\d+) ?to ?(?P<b>\d+)(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>\d+) ?to ?(?P<b>\d+)(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>\d+)\s*-\s*(?P<b>\d+)\s*=\s*(?P<desc>.*)"), # catch ranges with desc delimited by =
        re.compile(r"^\s*(?P<a>\d+)\s*=\s*(?P<desc>.*)"), # catch single vals with desc delimited by
        re.compile(r"^\s?[a-zA-Z:]*\s?(?P<a>\d+)\s*-\s*(?P<b>\d+)\s*=?\s*(?P<desc>.*)"), # catch base letter range vals
        re.compile(r"^\s*(?P<a>\d+)\s*–\s*(?P<b>\d+)\s*=?\s*(?P<desc>.*)"),  # special ascii
        re.compile(r"^\s*(?P<a>\d+)\s*=?\s*(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>[A-Z]+\d*)-(?P<b>[A-Z]+\d*)(?P<desc>.*)"), # catch base 36 ranges
        # removed star, was ?P<a>[A-Z]+\d*)*, check this hasn't broken things elsewhere
        re.compile(r"^\s*(?P<a>[A-Z]+\d*)(?P<desc>.*)"), # catch base 36 single val with description
    ]

    @staticmethod
    def extract_range_and_desc(possible_legal_value,python_type=str,hardfail=False,width=None):
        possible_legal_value = possible_legal_value.strip()
        possible_legal_value = possible_legal_value.strip('and')

        for regex in Range.RANGE_RE_LIST:
            m = regex.fullmatch(possible_legal_value)

            if m:
                a = m.group('a')
                desc = m.group('desc')
                if IN_INTEGER in a.lower():
                    a = "".rjust(width, '0')
                    b = "".rjust(width, '9')
                    return Range(a, b)
                elif IN_NULL in a.lower():  # if null in range return None, handled elsewhere
                    return None
                elif IN_ALPHANUMERIC in a.lower():  # if alphanumeric range must be handled differently
                    a = "".rjust(width, ' ')
                    b = "".rjust(width, 'z')
                    return Range(a, b)
                elif '!' in a:
                    return Range(a, a)
                elif IN_WHITESPACE in a.lower():  # informs if whitespace is legal, handled elsewhere
                    return None
                try:
                    b = m.group('b')
                except IndexError:
                    b = a

                if python_type == int:
                    for char in a:
                        if char.isalpha():
                            return None
                    for char in b:
                        if char.isalpha():
                            return None

                return Range(python_type(a), python_type(b), desc)

        if hardfail:
            raise ValueError("Cannot recognize range in: "+possible_legal_value)
        return None
        
    @staticmethod
    def combine_ranges(ranges):
        """Examine a list of ranges and combine adjacent ranges"""
        # Make a new list with the ranges in sorted order
        if None in ranges:
            ranges.remove(None)

        # I should remove the all int ranges, do the combining, and the re-added the non-int tranges
        if not all_ints(ranges):
            return ranges

        ranges = list(sorted(list(ranges), key=lambda r:(r.a,r.b)))
        # Combine r[i] and r[i+1] if they are touching or adjacent with no room between
        for i in range(len(ranges)-2,-1,-1):
            if ranges[i].b in [ranges[i+1].a,ranges[i+1].a-1]:
                ranges[i] = Range(ranges[i].a,ranges[i+1].b)
                ranges[i].b=ranges[i+1].b
                del ranges[i+1]
        return ranges

    __slots__ = ('date','desc','attrib','a','b')
    def __init__(self,a=None,b=None, desc=None, *, attrib={}):
        self.date   = False       # is this a date?
        self.desc   = desc
        self.attrib = attrib
        if type(a)==str and a.startswith("YYYYMMDD: "):
            self.date = "YYYYMMDD"
            a = a.replace("YYYYMMDD: ","")
        self.a = a
        self.b = b if b else a

    def __eq__(self,other):
        if other is None:
            return False
        assert type(other)==Range
        return (self.a==other.a) and (self.b==other.b)

    def __lt__(self,other):
        assert type(other)==Range
        return self.a < other.a

    def __repr__(self):
        if self.desc:
            return "Range({} - {}  {})".format(self.a,self.b,self.desc)
        else:
            return "Range({} - {})".format(self.a,self.b)
            

    def __contains__(self,val):
        return self.a <= val <= self.b

    def __hash__(self):
        return hash((self.a,self.b))

    def json_dict(self):
        if self.desc:
            {'a':self.a,'b':self.b,'desc':self.desc}
        return {'a':self.a,'b':self.b}

    def python_expr(self,python_type, width):
        if self.desc is not None and "Length" in self.desc:  # Handle OIDTB or other vals that require specific length
            return "len(str(x).strip()) == {}".format(self.b)

        """Return the range as a python expression in x"""
        if self.a == schema.RANGE_ANY or self.b == schema.RANGE_ANY:
            return "True "      # anything works

        if python_type==int or python_type==float:
            if self.a==self.b:
                return "x=={}".format(self.a)
            return "{} <= x <= {}".format(self.a,self.b)

        if python_type==str:
            """This needs to handle padding"""
            if self.a==self.b:
                if self.a == schema.RANGE_NULL:
                    return "x.strip()=='' "
                return "leftpad(x,{})==leftpad('{}',{})".format(width, self.a, width)
            return "between('{}',x,'{}',{})".format(self.a, self.b, width)

        logging.error("Cannot make python range expression for type %s",str(python_type))
        raise ValueError("Don't know how to create python range expression for type "+str(python_type))


    def is_int(self):
        return type(self.a)==int and type(self.b)==int


    def random_value(self):
        """Return a random value within the range"""
        if self.is_int():
            return random.randint(self.a,self.b+1)
        if self.a==self.b:
            return self.a
        if len(self.a)==1 and len(self.b)==1:
            return chr(random.randint(ord(self.a),ord(self.b)+1))
        if self.a[0:8]=='YYYYMMDD':
            return "19800101"   # not very random
        raise RuntimeError("Don't know how to make a random value for a={} ({}) b={} ({})".
                           format(self.a,type(self.a),self.b,type(self.b)))


