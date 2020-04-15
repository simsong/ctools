# dbfile.py

import datetime
import time
import os
import logging
import sys
import threading
import sqlite3

from collections import OrderedDict

"""
This is the dbfile.py (database file)

This package is mostly here for the MySQL interface, but parts can also be used with SQLite3. 

The goals of this package:

- Provide a higher-level abstraction for database access than provided by Python's built-in SQLite3 anad MySQL classes.

- Provide a more efficient interface than one typically gets using an Object Relation Mapper (ORM) such as SQLAlchemy.

- For MySQL, provide an easy-to-use mechanism for handling authentication.

- For MySQL, provide a system that allows for long-lived connections from an application to the MySQL database,
  but which automatically re-connects and retries the last transaction when the connection is interrupted. This means
  that connections need to be cached and to be atomic when at all possible.

- Make it easy to access internals.

- Make error handling easy.

- Make debugging easy.

- Eliminate code that tends to be repeated in applications that use a database.

The following classes are provided:

  DBSQL() - An abstract SQLDatbase class. Largely wraps the Python API.
  DBSqlite3(DBQSL) - DBSQL for SQLite3. The __init__ method lets one specify the file.
  DBMySQLAuth() - An authentication object for MySQL. Allows host, database, user, password to
                  be passed as a single parameter. Also holds a debug flag and a cached
                  database connection that uses these authentication parameters.

  DBMySQL(DBSQL) - DBSQL for MySQL. Includes logic for retrying, and a class method
                   that makes INSERT and SELECT an automic operation with automatic retry.
                 - *many* functions in this should probably be migrated to DBSQL().

The main DBMySQL class method that we use is:

  DBMySQL.csfr(auth, cmd, vals, quiet, rowcount, time_zone, get_column_names, asDicts, debug)
  
  "Connect, Select, FetchAll, Retry"

cmd - Statements should use "%s" for substituted arguments; this is turned to ? for SQLite3
    - Use INSERT IGNORE; this is turned to "INSERT OR IGNORE" for MySQL

When running as a server, credentials can be managed by storing them in a bash script.

For example, let's say you have a WSGI script that needs to know read-only MySQL credentails for a web application. You create a MySQL username called "dbreader" with the password "magic-password-1234" on your MySQL server at mysql.company.com. You give this user SELECT access to the database "database1". You might then create a script called 'dbreader.bash' and put it at /home/www/dbreader.bash:

   $ cat dbreader.bash
   export MYSQL_HOST="mysql.company.com"
   export MYSQL_USER="dbreader"
   export MYSQL_PASSWORD="magic-password-1234"
   export MYSQL_DATABASE="database1"
   alias dbreader="mysql -hMYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE"
   $

If you source this (which is not secure because it puts the password on the
command line, but hold that thought), you can then test out the dbreader account by just typing 'dbreader'. 

You can also use this bash script to provide credentials to your program using the DBMySQLAuth class:

   auth = DBMySQLAUTH("/home/www/dbreader.bash")

Then you can use auth as the first parameter in the .csfr() method.

Note: Currently, the end of this module also a methods for a remote system load
management system that was used to debug the persistent
connections. That's no longer and will be removed at a later date.


"""

MYSQL_HOST = 'MYSQL_HOST'
MYSQL_USER = 'MYSQL_USER'
MYSQL_PASSWORD = 'MYSQL_PASSWORD'
MYSQL_DATABASE = 'MYSQL_DATABASE'


CACHE_SIZE = 2000000
SQL_SET_CACHE = "PRAGMA cache_size = {};".format(CACHE_SIZE)

def timet_iso(t=time.time()):
    """Report a time_t as an ISO-8601 time format. Defaults to now."""
    return datetime.datetime.now().isoformat()[0:19]

def hostname():
    """Hostname without domain"""
    return socket.gethostname().partition('.')[0]

from abc import ABC, abstractmethod
class DBSQL(ABC):
    def __init__(self,dicts=True,debug=False):
        self.dicts = dicts
        self.debug = debug

    def __enter__(self):
        return self

    def __exit__(self,a,b,c):
        self.conn.close()

    def execute(self, cmd, *args, debug=False, **kwargs):
        if self.debug or debug:
            print(f"execute: {cmd}",file=sys.stderr)
            t0 = time.time()
        try:
            res = self.conn.cursor().execute(cmd, *args, **kwargs)
        except Exception as e:
            print(cmd,*args,file=sys.stderr)
            print(e,file=sys.stderr)
            exit(1)
        if self.debug or debug:
            t1 = time.time()
            print(f"time: {t1-t0}",file=sys.stderr)
        return res

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def create_schema(self, schema, *, debug=False):
        """Create the schema if it doesn't exist."""
        c = self.conn.cursor()
        for line in schema.split(";"):
            line = line.strip()
            if len(line)>0:
                if self.debug or debug:
                    print(f"{line};",file=sys.stderr)
                try:
                    c.execute(line)
                except Exception as e:
                    print("SQL:",line,file=sys.stderr)
                    print("Error:",e,file=sys.stderr)
                    exit(1)

    def execselect(self, sql, vals=()):
        """Execute a SQL query and return the first line"""
        c = self.conn.cursor()
        c.execute(sql, vals)
        return c.fetchone()

    def close(self):
        self.conn.close()

class DBSqlite3(DBSQL):
    def __init__(self,fname=None,*args,**kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.conn = sqlite3.connect(fname)
            if self.dicts:
                self.conn.row_factory = sqlite3.Row    # user wants dicts

        except sqlite3.OperationalError as e:
            print(f"Cannot open database file: {fname}")
            exit(1)

    def set_cache_bytes(self,b):
        self.execute(f"PRAGMA cache_size = {-b/1024}") # negative numbers are multiples of 1024

    # For sqlite3, csfr doesn't need to be a static method, because we don't disconnect from the database
    # Notice that we try to keep API compatiability, but we lose 'auth'. We also change '%s' into '?'
    def csfr(self, auth, cmd,vals=[],quiet=True, rowcount=None, time_zone=None,
             get_column_names=None, asDicts=False, debug=False, cache=True):
        assert auth is None
        assert get_column_names is None # not implemented yet
        cmd = cmd.replace("%s","?")
        cmd = cmd.replace("INSERT IGNORE","INSERT OR IGNORE")

        if quiet==False:
            print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}")
        if debug or self.debug:
            print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}",file=sys.stderr)

        try:
            c = self.conn.execute(cmd, vals)
        except (sqlite3.OperationalError,sqlite3.InterfaceError) as e:
            print(f"cmd: {cmd}",file=sys.stderr)
            print(f"vals: {vals}",file=sys.stderr)
            print(str(e),file=sys.stderr)
            raise RuntimeError("Invalid SQL")

        verb = cmd.split()[0].upper()
        if verb in ['INSERT','DELETE','UPDATE']:
            return
        elif verb in ['SELECT','DESCRIBE','SHOW']:
            return c.fetchall()
        else:
            raise RuntimeError(f"Unknown SQLite3 verb '{verb}'")


class DBMySQLAuth:
    """Class that represents MySQL credentials. Will cache the
connection. If run under bottle, the bottle object can be passed in,
and cached_db is stored in the request-local storage."""

    def __init__(self,*,host,database,user,password,bottle=None,debug=False):
        self.host     = host
        self.database = database
        self.user     = user
        self.password = password
        self.debug    = debug   # enable debugging
        self.dbcache  = dict()  # dictionary of cached connections.
        self.bottle   = bottle

    def __eq__(self,other):
        return ((self.host==other.host) and (self.database==other.database)
                and (self.user==other.user) and (self.password==other.password))

    def __hash__(self):
        return hash(self.host) ^ hash(self.database) ^ hash(self.user) ^ hash(self.password)

    def __repr__(self):
        return f"<DBMySQLAuth:{self.host}:{self.database}:{self.user}:*****:debug={self.debug}>"

    @staticmethod
    def GetBashEnv(filename):
        """Loads the bash environment variables specified by 'export NAME=VALUE' into a dictionary and returns it"""
        DB_RE = re.compile("export (.+)=(.+)")
        ret   = {}
        with open( filename ) as f:
            for line in f:
                m = DB_RE.search(line.strip())
                if m:
                    name = m.group(1)
                    val  = m.group(2)
                    # Check for quotes
                    if val[0] in "'\"" and val[0]==val[-1]: 
                        val = val[1:-1]
                    ret[name] = val
        return ret

    @staticmethod
    def FromEnv(filename):
        """Returns a DDBMySQLAuth formed by reading MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST and MYSQL_DATABASE envrionemtn variables from a bash script"""
        env = DBMySQLAuth.GetBashEnv(filename)
        return DBMySQLAuth(host = env[MYSQL_HOST], 
                           user = env[MYSQL_USER],
                           password = env[MYSQL_PASSWORD],
                           database = env[MYSQL_DATABASE])

    @staticmethod
    def FromConfig(section,debug=None):
        """Returns from the section of a config file"""
        try:
            return DBMySQLAuth(host = section[MYSQL_HOST], 
                               user = section[MYSQL_USER],
                               password = section[MYSQL_PASSWORD],
                               database = section[MYSQL_DATABASE],
                               debug    = debug )
        except KeyError as e:
            pass
        raise KeyError(f"config file section must have {MYSQL_HOST}, {MYSQL_USER}, {MYSQL_PASSWORD} and {MYSQL_DATABASE} sections")

    def cache_store(self,db):
        self.dbcache[ (os.getpid(), threading.get_ident()) ] = db

    def cache_get(self):
        return self.dbcache[ (os.getpid(), threading.get_ident()) ]

    def cache_clear(self):
        try:
            del self.dbcache[ (os.getpid(), threading.get_ident()) ]
        except KeyError as e:
            pass

RETRIES = 10
RETRY_DELAY_TIME = 1
class DBMySQL(DBSQL):
    """MySQL Database Connection"""
    def __init__(self, auth, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        if self.debug:
            print(f"Successfully connected to {auth}",file=sys.stderr)
        # Census standard TZ is America/New_York
        try:
            self.cursor().execute('SET @@session.time_zone = "America/New_York"')
        except internalError as e:
            pass
        self.cursor().execute('SET autocommit = 1') # autocommit

    RETRIES = 10
    RETRY_DELAY_TIME = 1
    @staticmethod
    def explain(cmd,vals):
        if (not isinstance(vals,list)) and (not isinstance(vals,tuple)) and (not vals is None):
            raise ValueError("vals is type %s expected list" % type(vals))
        def myquote(v):
            if isinstance(v,str):
                return "'"+v+"'"
            return str(v)
        if vals is not None:
            return cmd % tuple([myquote(v) for v in vals])
        else:
            return cmd
        
    @staticmethod
    def csfr(auth, cmd, vals=None, quiet=True, rowcount=None, time_zone=None,
             setup=None, setup_vals=(),
             get_column_names=None, asDicts=False, debug=False, dry_run=False, cache=True):
        """Connect, select, fetchall, and retry as necessary.
        @param auth      - authentication otken
        @param cmd       - SQL query
        @param vals      - values for SQL parameters
        @param setup     - An SQL statement that runs before cmd (typcially setting a variable)
        @param setup_vals - Values for SQL parameters for setup
        @param time_zone - if provided, set the session.time_zone to this value
        @param quiet     - don't print anything
        @param get_column_names - an array in which to return the column names.
        @param asDict    - True to return each row as a dictionary
        """

        if not isinstance(auth, DBMySQLAuth):
            raise ValueError(f"auth is type {type(auth)} expecting type {DBMySQLAuth}")
        debug = (debug or auth.debug)


        try:
            import mysql.connector.errors as errors
        except ImportError as e:
            import pymysql.err as errors
        for i in range(1,RETRIES):
            try:
                try:
                    db = auth.cache_get()
                except KeyError:
                    if i>1:
                        logging.error(f"Reconnecting. i={i}")
                    db = DBMySQL(auth)
                    auth.cache_store(db)
                result = None
                c      = db.cursor()
                c.execute('SET autocommit=1')
                if time_zone is not None:
                    c.execute('SET @@session.time_zone = "{}"'.format(time_zone)) # MySQL

                try:
                    if quiet==False or debug:
                        logging.warning("quiet:%s debug: %s cmd: %s  vals: %s",quiet,debug,cmd,vals)
                        logging.warning("EXPLAIN:")
                        logging.warning(DBMySQL.explain(cmd,vals))
                        
                    
                    ###
                    ###
                    if dry_run:
                        logging.warning("Would execute: %s,%s",cmd,vals)
                        return None

                    ### If there are multiple queries, execute them all.
                    ### Hopefully there is no semi-colon in a quoted string.
                    if setup is not None:
                        c.execute(setup, setup_vals)
                    c.execute(cmd,vals)
                    ###
                    ###

                    if (rowcount is not None) and (c.rowcount!=rowcount):
                        raise RuntimeError(f"{cmd} {vals} expected rowcount={rowcount} != {c.rowcount}")

                except (errors.ProgrammingError, errors.InternalError) as e:
                    logging.error("setup: %s",setup)
                    logging.error("setup_vals: %s", setup_vals)
                    logging.error("cmd: %s",cmd)
                    logging.error("vals: %s",vals)
                    logging.error("explained: %s ",DBMySQL.explain(cmd,vals))
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
                    if debug:
                        logging.warning("   SELECTED ROWS count=%s  row[0]=%s",len(result), result[0] if len(result)>0 else None)
                if verb in ['INSERT']:
                    result = c.lastrowid
                    if debug:
                        logging.warning("   INSERT c.lastworid=%s",c.lastrowid)
                if verb in ['UPDATE']:
                    result = c.rowcount
                c.close()  # close the cursor
                if i>1:
                    logging.error(f"Success with i={i}")
                return result
            except errors.InterfaceError as e:
                logging.error(e)
                logging.error(f"InterfaceError. threadid={threading.get_ident()} RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
                pass
            except errors.OperationalError as e:
                logging.error(e)
                logging.error(f"OperationalError. RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
                pass
            except errors.InternalError as e:
                logging.error(e)
                if "Unknown column" in str(e):
                    raise e
                logging.error(f"InternalError. threadid={threading.get_ident()} RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
                pass
            except BlockingIOError as e:
                logging.error(e)
                logging.error(f"BlockingIOError. RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
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

    

