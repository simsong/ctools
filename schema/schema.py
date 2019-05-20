import os
import sys

from collections import OrderedDict
import logging

from ctools.dconfig import dopen

import ctools.schema as schema
from ctools.schema import vtype_for_numpy_type
from ctools.schema import sql_parse_create
from ctools.schema.range import Range
from ctools.schema.table import Table
from ctools.schema.variable import Variable
from ctools.schema.recode import Recode

from types import ModuleType


class Schema:
    """A Schema is a collection of tables and recodes"""
    def __init__(self, name='', *, debug=False, attrib={}):
        self.debug     = debug
        self.tabledict = OrderedDict()        # by table name
        self.recodes = OrderedDict()
        self.tables_with_recodes = set()
        self.name    = name
        self.attrib  = attrib
        self.recode_module = ModuleType('recodemodule')


    def json_dict(self):
        return {"tables":{table.name:table.json_dict() for table in self.tables()}}

    def dump(self,func=print):
        func("Schema DUMP {}:".format(self.name))
        func("Tables: {}  Recodes: {}".format(len(self.tables()),len(self.recodes)))
        for table in self.tables():
            table.dump(func)
        for recode in self.recodes.values():
            recode.dump(func)

    def has_table(self,name):
        return name in self.tabledict

    def add_table(self,t):
        self.tabledict[t.name] = t
        logging.info("Added table {}".format(t.name))
        return t

    def add_table_named(self, *, name, **kwargs):
        return self.add_table( Table(name=name, **kwargs) )

    def get_table(self,name,create=False):
        """Get the named table. If create is true, create the table if it doesn't exist."""
        try:
            return self.tabledict[name]
        except KeyError as e:
            if create:
                table = Table(name=name)
                self.add_table(table)
                return table
            logging.error("Table {} requested; current tables: {}".format(name,self.table_names()))
            raise KeyError("Table {} does not exist".format(name))

    def tables(self):
        return self.tabledict.values()

    def table_names(self):
        return self.tabledict.keys()

    def sql_schema(self):
        return "\n".join([table.sql_schema() for table in self.tables()])
        
    ################################################################
    ### SQL Support
    ################################################################
    def add_sql_table(self,stmt):
        """Use the SQL parser to parse the create statement. Each parsed row is returned as a dictionary.
        The keys of the dictionary just happen to match the parameters for the Variable class.
        """
        sql = sql_parse_create(stmt)
        table = Table(name=sql[schema.SQL_TABLE])
        for vdef in sql[schema.SQL_COLUMNS]:
            v = Variable(vtype=vdef['vtype'],name=vdef['name'])
            table.add_variable(v)
        self.add_table(table)


    ################################################################
    ### Pandas support
    ################################################################
    def get_pandas_file_reader(self,filename,chunksize=schema.PANDAS_CHUNKSIZE):
        (base,ext) = os.path.splitext(filename)
        import pandas
        if ext==schema.SAS7BDAT_EXT:
            return pandas.read_sas( dopen(filename), chunksize=chunksize, encoding='latin1')
        if ext==schema.CSV_EXT:
            return pandas.read_csv( dopen(filename), chunksize=chunksize, encoding='latin1')
        if ext==schema.TXT_EXT:
            # Get the first line and figure out the seperator
            with dopen(filename) as f:
                line = f.readline()
            if line.count("|") > 2:
                sep='|'
            elif line.count("\t") > 2:
                sep='\t'
            else:
                sep=','
            logging.info('sep={}'.format(sep))
            return pandas.read_csv( dopen(filename), chunksize=chunksize, sep=sep, encoding='latin1')
        logging.error("get_pandas_file_reader: unknown extension: {}".format(ext))
        raise RuntimeError("get_pandas_file_reader: unknown extension: {}".format(ext))


    ################################################################
    ### Load tables from a specification file
    ################################################################
    def load_schema_from_file(self,filename):

        if filename.endswith(".docx"):
            raise RuntimeError("Schema cannot read .docx files; you probably want to use CensusSpec")

        if filename.endswith(".xlsx"):
            raise RuntimeError("Schema cannot read .docx files; you probably want to use CensusSpec")

        # Make a table
        table_name = os.path.splitext(os.path.split(filename)[1])[0]
        table_name = table_name.replace("-","_")
        table = Table(name=table_name)
        table.filename = filename
        table.add_comment("Parsed from {}".format(filename))

        # Load the schema from the data file.
        # This will use pandas to read a single record.
        for chunk in self.get_pandas_file_reader(filename,chunksize=1):
            for row in chunk.to_dict(orient='records'):
                for colName in chunk.columns:
                    v = Variable()
                    v.set_name(colName)
                    v.set_vtype(vtype_for_numpy_type(type(row[colName])))
                    table.add_variable(v)
                self.add_table(table)
                return

    ################################################################
    ### Read records support
    ################################################################
    def read_records_as_dicts(self,*,filename=None,tablename,limit=None,random=False):
        table = self.get_table(tablename)
        if filename==None and table.filename:
            filename = table.filename
        count = 0
        
        if random:
            # Just make up random records
            assert limit>0
            for count in range(limit):
                yield table.random_dict_record()
            return

        # Get pandas file reader if we have one
        reader = self.get_pandas_file_reader(filename)
        if reader:
            for chunk in reader:
                for row in chunk.to_dict(orient='records'):
                    yield(row)
                    count +=1
                    if limit and count>=limit:
                        return
        else:
            with open(filename,"r") as f:
                for line in f:
                    data = table.parse_line_to_dict(line)
                    yield data
                    count +=1 
                    if limit and count>=limit:
                        break

    ################################################################
    ### Recode support
    ################################################################

    def recode_names(self):
        """Return an array of all the recode names"""
        return [r.name for r in self.recodes.values()]

    def add_recode(self,name,vtype,desc):
        """Add a recode, and create the variable for the recode in the destination table"""
        assert type(name)==str
        assert type(vtype)==str
        assert type(desc)==str
        assert desc.count("=")==1
        r = Recode(name=name, desc=desc)
        v = Variable(name=r.dest_table_var, vtype=vtype)
        self.get_table(r.dest_table_name).add_variable(v)
        self.recodes[name]=r
        self.tables_with_recodes.add(r.dest_table_name)

    def compile_recodes(self):
        """The recode function is a function called recode() in the self.recode_module.
        Global variables are put in the module for each variable in every table. When the recode module is called,
        additional global variables are created for the data of every line that has been read, and the dictionary of data being recoded."""

        # Add the variables for every table
        for table in self.tables():
            for v in table.vardict.values():
                self.recode_module.__dict__[v.name] = v.name

        self.recode_func = "def recode():\n"
        for recode in self.recodes.values():
            self.recode_func += "    {}\n".format(recode.statement)
        self.recode_func += "    return\n" # terminate the function (useful if there are no recodes)
        compiled = compile(self.recode_func, '', 'exec')
        exec(compiled, self.recode_module.__dict__)
        # Now create empty directories to receive the variables for the first recode
        for tablename in self.tables_with_recodes:
            self.recode_module.__dict__[tablename] = {}

    def recode_load_data(self,tablename,data):
        self.recode_module.__dict__[tablename] = data

    def recode_execute(self,tablename,data):
        if tablename not in self.tables_with_recodes:
            return
        self.recode_module.__dict__[tablename] = data
        try:
            self.recode_module.recode()
        except Exception as e:
            print("Error in executing recode.",file=sys.stderr)
            print("tablename: {}  data: {}".format(tablename,data),file=sys.stderr)
            print("Recode function:",file=sys.stderr)
            print(self.recode_func,file=sys.stderr)
            print(e,file=sys.stderr)
            print("tables with recodes: {}".format(self.tables_with_recodes),file=sys.stderr)
            print("recode environment:",file=sys.stderr)
            print("defined variables:",file=sys.stderr)
            for v in sorted(self.recode_module.__dict__.keys(),file=sys.stderr):
                print("   ",v,file=sys.stderr)
            raise e


    ################################################################
    ### Overrides
    ################################################################
    def create_overrides(self,keyword):
        """An override is a set of per-table values for variables. They are found by searching for a keyword
        in the description of allowable variables. Once found, they are automatically applied when records are written.
        """
        for table in self.tables():
            table.create_overrides(keyword)


    ### Defaults
    def find_default_from_allowable_range_descriptions(self,text):
        """Call this for every table. We do that a lot; perhaps we need an @every decorator or something"""
        for table in self.tables():
            table.find_default_from_allowable_range_descriptions(text)


if __name__=="__main__":
    from argparse import ArgumentParser,ArgumentDefaultsHelpFormatter
    parser = ArgumentParser( formatter_class = ArgumentDefaultsHelpFormatter,
                             description="Test functions for the schema module" )
    parser.add_argument("--dumpfile", help="examine a FILE and dump its schema")
    args = parser.parse_args()
    if args.dumpfile:
        db = Schema()
        db.load_schema_from_file(args.dumpfile)
        db.dump(print)
        print(db.sql_schema())

    
