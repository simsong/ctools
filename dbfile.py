#
# Methods that return File(pathid,dirname,filename) for searches
#

import datetime
import time
import os
import logging
import sys
from collections import OrderedDict

CACHE_SIZE = 2000000
SQL_SET_CACHE = "PRAGMA cache_size = {};".format(CACHE_SIZE)

def timet_iso(t=time.time()):
    """Report a time_t as an ISO-8601 time format. Defaults to now."""
    return datetime.datetime.now().isoformat()[0:19]

def hostname():
    """Hostname without domain"""
    return socket.gethostname().partition('.')[0]

class DBSQL:
    def __enter__(self):
        return self

    def __exit__(self,a,b,c):
        self.conn.close()

    def create_schema(self,schema):
        """Create the schema if it doesn't exist."""
        c = self.conn.cursor()
        for line in schema.split(";"):
            line = line.strip()
            if len(line)>0:
                print(line)
                c.execute(line)

    def execselect(self, sql, vals=()):
        """Execute a SQL query and return the first line"""
        c = self.conn.cursor()
        c.execute(sql, vals)
        return c.fetchone()

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

class DBSqlite3(DBSQL):
    def __init__(self,*,fname=None):
        try:
            import sqlite3
            self.conn = sqlite3.connect(fname)
        except sqlite3.OperationalError as e:
            print(f"Cannot open database file: {fname}")
            exit(1)
        

class DBMySQLAuth:
    def __init__(self,*,host,database,user,password):
        self.host     = host
        self.database = database
        self.user     =user
        self.password = password
        self.debug    = False   # enable debugging
        self.cached_db= None    # cached connection


    def __eq__(self,other):
        return ((self.host==other.host) and (self.database==other.database)
                and (self.user==other.user) and (self.password==other.password))

    def __hash__(self):
        return hash(self.host) ^ hash(self.database) ^ hash(self.user) ^ hash(self.password)

    def __repr__(self):
        return f"<DBMySQLAuth:{self.host}:{self.database}:{self.user}:*****>"




RETRIES = 10
RETRY_DELAY_TIME = 1
class DBMySQL(DBSQL):
    """MySQL Database Connection"""
    def __init__(self,auth):
        try:
            import mysql.connector as mysql
            internalError = RuntimeError
        except ImportError as e:
            try:
                import pymysql
                import pymysql as mysql
                internalError = pymysql.err.InternalError
            except ImportError as e:
                print(f"Please install MySQL connector with 'conda install mysql-connector-python' or the pure-python pymysql connector")
                raise ImportError()
                
        self.conn = mysql.connect(host=auth.host,
                                  database=auth.database,
                                  user=auth.user,
                                  password=auth.password)
        # Census standard TZ is America/New_York
        try:
            self.cursor().execute('SET @@session.time_zone = "America/New_York"')
        except internalError as e:
            pass
        self.cursor().execute('SET autocommit = 1') # autocommit

    RETRIES = 10
    RETRY_DELAY_TIME = 1
    @staticmethod
    def csfr(auth,cmd,vals=None,quiet=True,rowcount=None,time_zone=None,
             get_column_names=None,asDicts=False,debug=False):
        """Connect, select, fetchall, and retry as necessary.
        @param auth      - authentication otken
        @param cmd       - SQL query
        @param vals      - values for SQL parameters
        @param time_zone - if provided, set the session.time_zone to this value
        @param quiet     - don't print anything
        @param get_column_names - an array in which to return the column names.
        @param asDict    - True to return each row as a dictionary
        """

        debug = (debug or auth.debug)


        try:
            import mysql.connector.errors as errors
        except ImportError as e:
            import pymysql.err as errors
        for i in range(1,RETRIES):
            try:
                if auth.cached_db is None:
                    auth.cached_db = DBMySQL(auth)
                db = auth.cached_db
                result = None
                c = db.cursor()
                c.execute('SET autocommit=1')
                if time_zone is not None:
                    c.execute('SET @@session.time_zone = "{}"'.format(time_zone)) # MySQL
                try:
                    if quiet==False:
                        print(f"cmd:{cmd} vals:{vals}")
                    if debug:
                        print(f"cmd:{cmd} vals:{vals}",file=sys.stderr)
                    
                    ###
                    ###
                    c.execute(cmd,vals)
                    ###
                    ###

                    if (rowcount is not None) and (c.rowcount!=rowcount):
                        raise RuntimeError(f"{cmd} {vals} expected rowcount={rowcount} != {c.rowcount}")
                except errors.ProgrammingError as e:
                    logging.error("cmd: "+str(cmd))
                    logging.error("vals: "+str(vals))
                    logging.error(str(e))
                    raise e
                except TypeError as e:
                    logging.error(f"TYPE ERROR: cmd:{cmd} vals:{vals} {e}")
                    raise e
                verb = cmd.split()[0].upper()
                if verb in ['SELECT','DESCRIBE','SHOW']:
                    result = c.fetchall()
                    if asDicts and get_column_names is None:
                        get_column_names = []
                    if get_column_names is not None:
                        get_column_names.clear()
                        for (name,type_code,display_size,internal_size,precision,scale,null_ok) in c.description:
                            get_column_names.append(name)
                    if asDicts:
                        result =[OrderedDict(zip(get_column_names, row)) for row in result]
                if verb in ['INSERT']:
                    result = c.lastrowid
                c.close()  # close the cursor
                return result
            except errors.InterfaceError as e:
                logging.error(e)
                logging.error(f"InterfaceError. RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cached_db = None
                pass
            except errors.OperationalError as e:
                logging.error(e)
                logging.error(f"OperationalError. RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cached_db = None
                pass
            except BlockingIOError as e:
                logging.error(e)
                logging.error(f"BlockingIOError. RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cached_db = None
                pass
            time.sleep(RETRY_DELAY_TIME)
        raise RuntimeError("Retries Exceeded")


    @staticmethod
    def table_columns(auth, table_name):
        """Return a dictionary of the schema. This should probably be upgraded to return the ctools schema"""
        return [row[0] for row in DBMySQL.csfr(auth, "describe "+table_name)]
                    

################################################################
##
## memory profiling tools
##

def maxrss():
    """Return maxrss in bytes, not KB"""
    return resource.getrusage(resource.RUSAGE_SELF)[2]*1024 

def print_maxrss():
    for who in ['RUSAGE_SELF','RUSAGE_CHILDREN']:
        rusage = resource.getrusage(getattr(resource,who))
        print(who,'utime:',rusage[0],'stime:',rusage[1],'maxrss:',rusage[2])

def mem_info(what,df,dump=True):
    import pandas as pd
    print(f'mem_info {what} ({type(df)}):')
    if type(df)!=pd.core.frame.DataFrame:
        print("Total {} memory usage: {:}".format(what,total_size(df)))
    else:
        if dump:
            pd.options.display.max_columns  = 240
            pd.options.display.max_rows     = 5
            pd.options.display.max_colwidth = 240
            print(df)
        for dtype in ['float','int','object']: 
            selected_dtype = df.select_dtypes(include=[dtype])
            mean_usage_b = selected_dtype.memory_usage(deep=True).mean()
            mean_usage_mb = mean_usage_b / 1024 ** 2
            print("Average {} memory usage for {} columns: {:03.2f} MB".format(what,dtype,mean_usage_mb))
        for dt in ['object','int64']:
            for c in df.columns:
                try:
                    if df[c].dtype==dt:
                        print(f"{dt} column: {c}")
                except AttributeError:
                    pass
        df.info(verbose=False,max_cols=160,memory_usage='deep',null_counts=True)
    print("elapsed time at {}: {:.2f}".format(what,time.time() - start_time))
    print("==============================")


def get_free_mem():
    return psutil.virtual_memory().available

REPORT_FREQUENCY = 60           # report this often
last_report = 0                 # last time we reported
def report_load_memory(auth):
    """Report and print the load and free memory; return free memory"""
    global last_report
    free_mem = get_free_mem()

    # print current tasks
    # See https://stackoverflow.com/questions/2366813/on-duplicate-key-ignore regarding
    # why we should not use "INSERT IGNORE"
    if last_report < time.time() + REPORT_FREQUENCY:
        DBMySQL.csfr(auth,"insert into sysload (t, host, min1, min5, min15, freegb) "
                     "values (now(), %s, %s, %s, %s, %s) "
                     "ON DUPLICATE KEY update min1=min1", 
                     [HOSTNAME] + list(os.getloadavg()) + [get_free_mem()//GiB],
                     quiet=quiet)
        last_report = time.time()

    

