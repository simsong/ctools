import re
import logging
import random

import ctools.schema  as schema
from ctools.schema import clean_int

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
        re.compile(r"^\s*(?P<a>\d+)\s*-\s*(?P<b>\d+)\s*=\s*(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>\d+)\s*=\s*(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>\d+)\s*-\s*(?P<b>\d+)\s*=?\s*(?P<desc>.*)"),
        re.compile(r"^\s*(?P<a>\d+)\s*=?\s*(?P<desc>.*)")
    ]

    @staticmethod
    def extract_range_and_desc(possible_legal_value,python_type=str,hardfail=False,width=None):
        possible_legal_value = possible_legal_value.strip()
        possible_legal_value = possible_legal_value.strip('and')
        if possible_legal_value.count("=")>1:
            logging.error("invalid possible legal values: {} ({})".format(possible_legal_value,possible_legal_value.count("=")))
            return None
        for regex in Range.RANGE_RE_LIST:
            if ("-" in possible_legal_value and "=" in possible_legal_value):
                equal_index = possible_legal_value.index("=")
                hyphen_index = possible_legal_value.index("-")
                if equal_index < hyphen_index:
                    m = Range.RANGE_RE_LIST[1].search(possible_legal_value)
                else:
                    m = Range.RANGE_RE_LIST[0].search(possible_legal_value)
            else:
                m = regex.search(possible_legal_value)
            if m:
                a = m.group('a')
                desc = m.group('desc')
                try:
                    b = m.group('b')
                except IndexError:
                    b = a
                return Range(python_type(a), python_type(b), desc)

        if hardfail:
            raise ValueError("Cannot recognize range in: "+possible_legal_value)
        return None

        #if ("=" not in possible_legal_value) and ("-" not in possible_legal_value) and (len(possible_legal_value)>10):
        #    return None
        #if "=" in possible_legal_value:
        #    (rng,desc) = possible_legal_value.split("=")
        #else:
        #    (rng,desc) = (possible_legal_value, "")
        #if "-" in rng:
        #    (r0,r1) = rng.split("-")
        #else:
        #    r0 = r1 = rng
        #return (convertRange(r0,r1), desc)
        
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

        if int(self.a) < 0:
            whitespace = ""
            for i in range(len(str(self.a))-2):
                whitespace = whitespace + " "
            return "x=='{}'".format(whitespace)

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


