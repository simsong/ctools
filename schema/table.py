import os
import logging

from ctools.schema import valid_sql_name,SCHEMA_SUPPORT_FUNCTIONS,SQL_SCHEMA, MYSQL, SQLITE3, SQL_TYPE_MAP, sql_type_for_python_value
from ctools.schema.variable import Variable
from collections import OrderedDict


class Table:
    """A class to represent a table in a database. 
    Tables consist of variables, comments, overrides, and other data. 
    Table definitions can be learned from many sources, including:
       * SQL statements
       * A Microsoft Word table
       * A pandas data frame
       * Hand-assembled.
       * An importer, that might import from a Microsoft Word Table, or a SAS command file.
    """
    __slots__ = ('filename','name','desc', 'version','vardict','comments','overrides','attrib',
                 'csv_file','csv_writer', 'delimiter')

    def __init__(self,*,name,desc=None,attrib={},csv_file=None,csv_writer=None,delimiter=None):
        if not valid_sql_name(name):
            raise RuntimeError("invalid SQL Table name: {}".format(name)) 
        self.filename   = None    # filename from which table was read
        self.name       = name.replace(" ","_").replace(".","_")       # name of this table, change spaces to dots
        self.version    = None
        self.vardict    = OrderedDict() # an ordered list of the variables, by name
        self.desc       = desc
        self.comments   = []
        self.overrides  = {}      # variable:value
        self.attrib     = attrib
        self.csv_file   = csv_file
        self.csv_writer = csv_writer
        self.delimiter  = delimiter
        
    def __repr__(self):
        return f"<schema.table name:{self.name} {len(self.vardict)} vars>"

    @classmethod
    def FromDict(self,name,dict={}):
        """Create a table from a dictionary. Only handles non-container types as dictionary values."""
        t = self(name=name)
        for (k,v) in dict.items():
            t.add_variable( Variable(name=k, python_type=type(v)))
        return t

    def json_dict(self):
        """Provide a JSON dict of the table name and variables"""
        return {"name":self.name,
                "variables":[var.json_dict() for var in self.vars()]}

    def dump(self,func=print):
        """Dump Table in a human-readable form"""
        func(f"Table: {self.name} {self.desc} "
             f"version:{self.version}  #variables:{len(self.vars())}")
        if self.attrib:
            func(f"Table attributes: {self.attrib}")
        for var in self.vars():
            var.dump(func)

    def add_comment(self,comment):
        """Add comments to the comments string"""
        self.comments.append(comment)

    ###
    ### Variable management
    ###

    def vars(self):
        """We need a list of the variables so much, this returns it"""
        return self.vardict.values()

    def varnames(self):
        """Provide a list of variable names"""
        return self.vardict.keys()

    def fields(self):
        return {v.field:v for v in self.vardict.values()}

    def python_name(self):
        return self.name.replace(".","_").replace(" ","_")

    def get_variable(self,name):
        """Get a variable by name"""
        return self.vardict[name]

    def add_variable(self,var):
        """Add a Variable"""
        assert isinstance(var,Variable)
        if var.name in self.vardict:
            raise RuntimeError("Variable {} already in table {}".format(var.name,self.name))

        if self.delimiter is not None:
            if var.field is None:
                raise RuntimeError("Table has delimiter, so variable {} requires a field".format(var))
            if var.field in [v.field for v in self.vars()]:
                raise RuntimeError("Field {} is already taken, so variable {} cannot be added".
                                   format( var.field, var ))

        self.vardict[var.name] = var
        logging.info(f"Table {self.name}: Added variable {var}")

    def create_overrides(self,keyword):
        for var in self.vars():
            for r in var.ranges:
                if keyword in r.desc:
                    self.overrides[var.name] = r.a # we only override with the first element of the range

    ###
    ### Data generation tools
    ###
    def random_file_record(self,delim='|'):
        """Returns a random file record"""
        return delim.join([str(v.random_value()) for v in self.vars()])

    def random_dict_record(self):
        """Returns a random record as a dictionary"""
        return dict( [ (v.name,v.random_value()) for v in self.vars() ] )

    def default_record(self):
        """Returns a record with the defaults"""
        ret = {}
        for v in self.vars():
            if not (v.default is None):
                ret[v.name] = v.default
        return ret
        
    ###
    ### Reverse compilers (create code that is compiled)
    ###

    def sas_definition(self):
        """Generate a SAS table definition for this table"""
        vars = " ".join(self.varnames())
        tablename = self.name.upper().replace(".","").replace(" ","")
        tablefn = tablename+".txt"
        return SAS_TEMPLATE.format(tablefn,tablename,vars,tablename)

    def python_class(self,ignore_vars=[]):
        """Generate a Python validator and class for a table element. Ignore any variables specified in ignore_vars"""
        ret  = []
        ret.append(SCHEMA_SUPPORT_FUNCTIONS)
        ret.append("")
        ret.append("class {}_validator:".format(self.python_name()))
        ret.append("".join([var.python_validator() for var in self.vars()]))
        ret.append("    @classmethod")
        ret.append("    def validate_pipe_delimited(self,x):".format(self.python_name()))
        ret.append("        fields = x.split('|')")
        ret.append("        if len(fields)!={}: return False".format(len(self.vars())))
        for (i,v) in enumerate(self.vars(), 1):
            if v.name in ignore_vars:
                continue
            ret.append("        if {}(fields[{}]) == False: return False".
                           format(v.python_validator_name(),i))
        ret.append("        return True")
        ret.append("")
        ret.append("class {}:".format(self.python_name()))
        ret.append("    __slots__ = [" + ", ".join(["'{}'".format(var.name) for var in self.vars()]) + "]")
        ret.append("    def __repr__(self):")
        ret.append("        return '{}<".format(self.python_name()) +
                   ",".join(["%s:{}" % var.name for var in self.vars()]) + ">'.format(" +
                   ",".join(["self.%s" % var.name for var in self.vars()]) + ')')
        
        ret.append("    def __init__(self,line=None):")
        ret.append("        if line: ")
        ret.append("            if '|' in line: ")
        ret.append("                self.parse_pipe_delimited(line)")
        ret.append("            else:")
        ret.append("                self.parse_column_specified(line)")
        ret.append("    @classmethod")
        ret.append("    def name(self):")
        ret.append("        return '{}'".format(self.python_name()))
        ret.append("")
        ret.append("    def parse_pipe_delimited(self,line):")
        ret.append("        fields = line.split('|')")
        ret.append("        if len(fields)!={}:".format(len(self.vars())))
        ret.append("            raise ValueError(f'expected {} fields, found {}')".
                   format(len(self.vars()),"{len(fields)}"))
        for (i,v) in enumerate(self.vars(), 0):
            if v.name in ignore_vars:
                continue
            ret.append("        self.{:15} = fields[{}]  # {}".format(v.name,i,v.desc))

        ret.append("")
        ret.append("    def parse_column_specified(self,line):")
        for var in self.vars():
            if (var.column==None) or (var.width==None) or (var.name in ignore_vars):
                ret.append("        self.{:15} = None   # no column information for {}".format(var.name,var.name))
            else:
                ret.append("        self.{:15} = line[{}:{}] # {}".format(
                    var.name, var.column, var.column+var.width, var.desc))

        ret.append("")
        ret.append("    def validate(self):")
        ret.append('        """Return True if the object data validates"""')
        for var in self.vars():
            if var.name in ignore_vars:
                continue
            ret.append("        if not %s_validator.is_valid_%s(self.%s): return False" %
                       (self.python_name(), var.name, var.name))
        ret.append("        return True")
        ret.append("")
        ret.append("    def validate_reason(self):")
        ret.append("        reason=[]")
        for var in self.vars():
            if var.name in ignore_vars:
                continue
            ret.append("        if not %s_validator.is_valid_%s(self.%s): "
                       "reason.append('%s ('+str(self.%s)+') out of range (%s)')" %
                       (self.python_name(), var.name, var.name, var.name, var.name,
                        var.python_validation_text()))
        ret.append("        return ', '.join(reason)")

        ret.append("")
        ret.append("    def SparkSQLRow(self):")
        ret.append('        """Return a SparkSQL Row object for this object."""')
        ret.append('        from pyspark.sql import Row')
        ret.append('        return Row(')
        for var in self.vars():
            if var.name in ignore_vars:
                continue
            ret.append("            {name_lower}=safe_{python_type}(self.{name}),"
                       .format(name_lower=var.name.lower(),
                               python_type=var.python_type.__name__,
                               name=var.name))
        ret.append('        )')
        ret.append('\n')

        ret.append("    @staticmethod")
        ret.append("    def parse_line(line):")
        ret.append("        # Read a line and return it as a dictionary.")
        ret.append("        inst: CEF20_UNIT = CEF20_UNIT()")
        ret.append("        inst.parse_column_specified(line)")
        ret.append("        assert inst.validate(), f'A line is invalid!! line: {line}, validate_reason: {inst.validate_reason()}'")
        ret.append("        row = inst.SparkSQLRow()")
        ret.append("        return row\n")
        return "\n".join(ret) + "\n"

    def sql_schema(self, extra={}):
        """Generate CREATE TABLE statement for this schema"""
        ret = []
        for line in self.comments:
            ret.append("-- {}".format(line))
        ret.append("CREATE TABLE {} (".format(self.name))
        names = list(self.varnames()) + list(extra.keys())
        print("names:",names)
        descs = [v.desc for v in self.vars()] + [''] * len(extra)
        types = [v.sql_type() for v in self.vars()] + [sql_type_for_python_value(v) for v in extra.values()]
        for (n,d,t) in zip(names,descs,types):
            sep_comma   = ','    if n!= names[-1] else ''
            sep_comment = '--'   if d else ''
            ret.append("   {} {}{} {} {}".format(n, t, sep_comma, sep_comment, d))
        ret.append(");")
        return "\n".join(ret)+"\n"

    def sql_insert(self, dialect=MYSQL, extra={}):
        """Generate a prepared INSERT INTO statement for this schema"""
        param = SQL_SCHEMA[dialect]['param']
        return "INSERT INTO {} ".format(self.name) +\
            "(" + ",".join( list(self.varnames()) + list(extra)) + ") " +\
            "VALUES (" + ",".join( [param] * (len(self.vars())  + len(extra))) + ");"
        
    def sql_prepare(self):
        lines = []
        i = 0
        for (i,v) in enumerate(self.vars(), 1):
            if not v.column:
                raise RuntimeError("NO COLUMN FOR {}".format(v.name))
            (start,end) = v.column
            assert start<=end
            s = None
            if v.vtype in [schema.TYPE_INTEGER, schema.TYPE_NUMBER]:
                s = "if (sqlite3_bind_int( s, {}, get_int( line, {}, {})) != SQLITE_OK) error({});"\
                    .format(i+1, start, end, i+1)
            if v.vtype in [schema.TYPE_CHAR, schema.TYPE_VARCHAR]:
                s = ("if (sqlite3_bind_text( s, {}, get_text( line, buf, sizeof(buf), {}, {}), "
                     "{}, SQLITE_TRANSIENT) != SQLITE_OK) error({});"
                     .format(i+1, start, end, start, i+1))
            if s==None:
                raise RuntimeError("Cannot compile {} type {}".format(v.name,v.vtype))
            lines.append(s)
        return "\\\n".join(lines)
                
    def write_sql_scanner(self,f):
        data_line_len = max([v.column[1] if (v.column is not None) else 0 for v in self.vars()])

        f.write('#define SQL_CREATE "{}"\n'.format(self.sql_schema().replace("\n"," ")))
        f.write('#define SQL_INSERT "{}"\n'.format(self.sql_insert()))
        f.write("#define SQL_PREPARE(s,line)\\\n{}\n".format(self.sql_prepare()))
        f.write("#define DATA_LINE_LEN {}\n".format( data_line_len ))
    
    ###
    ### Methods for working with data defined by this schema
    ###

    def open_csv(self,fname,delimiter=',',extra=[],mode='w',write_header=True):
        import csv
        """Open a CSV file for this table"""
        logging.info("open_csv('{}','{}')".format(fname,mode))
        if os.path.exists(fname) and mode!='a':
            logging.error("{}: exists".format(fname))
            raise RuntimeError("{}: exists".format(fname))
        self.csv_file  = open(fname,mode, newline="", encoding='utf-8')
        self.csv_writer= csv.writer(self.csv_file, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        if write_header:
            self.csv_writer.writerow(list(self.varnames()) + extra)

    ###
    ### parsing
    ###

    def parse_line_to_row(self, line, delimiter=None):
        """Parse a line using the current table schema and return an array of values. 
        Much more efficient than extracting variables one at a time.""" 
        assert len(self.vars()) > 0
        if delimiter is None:
            delimiter = self.delimiter
        if delimiter is not None:
            fields = line.split(delimiter)
            return [v.python_type( fields[v.field] ) for v in self.vars() ]
        for v in self.vars:
            if v.start is not None and v.end is not None and v.width is not None:
                if v.width - 1 + v.start != v.end:
                    raise RuntimeError("Specified width did not line up with specified start and end of var {}".format(v.name))

        return [ v.python_type(line[ v.start -1: v.end]) for v in self.vars() if (v.start is not None and v.end is not None)]

    def parse_line_to_dict(self, line, delimiter=None):
        """Parse a line (that was probably read from a text file) 
        using the current table schema and return a dictionary of values.
        If no delimiter is specified, assumes that the line is column-specified.
        """
        assert len(self.vars()) > 0
        if delimiter is None:
            delimiter = self.delimiter
        if delimiter is not None:
            fields = line.split(delimiter)
            return { v.name:v.python_type( fields[ v.field] ) for v in self.vars() }
        return { v.name:v.python_type(line[ v.column: v.column+v.width]) for v in self.vars() if (v.column is not None)}

    def parse_and_write_line(self, line,extra=[]):
        self.write_row(self.parse_line_to_row(line), extra=extra)

    def parse_line_to_SparkSQLRow(self, line):
        from pyspark.sql import Row
        return Row( **self.parse_line_to_dict( line ) )

    ###
    ### writing
    ###

    def unparse_dict_to_line(self,d,delimiter=','):
        return delimiter.join([v.vformat(self.overrides.get(v.name,d[v.name])) for v in self.vars()])

    def write_dict(self,d):
        """Write a dict using the current .csv_writer. Honors overrides."""
        try:
            self.csv_writer.writerow( [v.vformat(self.overrides.get(v.name,d[v.name])) for v in self.vars()] )
        except KeyError as e:
            logging.error("*****************   KeyError Error in write_dict for table {} **************".format(self.name))
            logging.error("varnames: {}".format(self.varnames()))
            logging.error("overrides: {}".format(self.overrides))
            logging.error("d: {}".format(d))
            logging.error("d is missing the following keys:")
            for key in self.varnames():
                if key not in d:
                    logging.error("   {}".format(key))
            logging.error("self.vars():")
            for v in self.vars():
                logging.error(str(v))
            raise e

    def find_default_from_allowable_range_descriptions(self,text):
        """Call this for every variable. We do that a lot; perhaps we need an @every decorator or something"""
        for var in self.vars():
            var.find_default_from_allowable_range_descriptions(text)

    def extract_variable_from_line(self,varname,line):
        v = self.vardict[varname]
        return line[ v.column[0]: v.column[1]+1]

    def write_row(self,row,extra=[]):
        """Write a row using the CSV writer"""
        self.csv_writer.write_row( row + extra)



