# dbfile.py


from os.path import basename, abspath, dirname
from collections import OrderedDict
from abc import ABC, abstractmethod
import datetime
import time
import os
import os.path
import logging
import sys
import threading
import json
import sqlite3
import socket
import re
import pymysql
import configparser

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    pass


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

   auth = ctools.dbfile.DBMySQLAuth.GetBashEnvFromFile("/home/www/dbreader.bash")

Then you can use auth as the first parameter in the .csfr() method.

Other methods include:

   auth = ctools.dbfile.DBMySQLAuth.FromConfig() # reads from a config.ini file

Note: Currently, the end of this module also a methods for a remote system load
management system that was used to debug the persistent
connections. That's no longer and will be removed at a later date.

The following static methods are available:

GetBashEnvFromFile( fname )
FromBashEnvFile( fname )
FromConfig( section )
FromConfigFile( fname, section)
FromEnv()

"""

# Original names
MYSQL_HOST = 'MYSQL_HOST'
MYSQL_USER = 'MYSQL_USER'
MYSQL_PASSWORD = 'MYSQL_PASSWORD'
MYSQL_DATABASE = 'MYSQL_DATABASE'
MYSQL_PORT  = 'MYSQL_PORT'
MYSQL_DEFAULT_PORT = 3306
# Errors we do not retry. This used to be a long list, but it got shortened?
ERRORS_NO_RETRY = []

# new names
HOST = 'HOST'
USER = 'USER'
PASSWORD = 'PASSWORD'
DATABASE = 'DATABASE'

AWS_SECRET_NAME = 'AWS_SECRET_NAME'
AWS_REGION_NAME = 'AWS_REGION_NAME'
SECRETSMANAGER = 'secretsmanager'
DEFAULT_PORT = 3306
CACHE_SIZE = 2000000
SQL_SET_CACHE = "PRAGMA cache_size = {};".format(CACHE_SIZE)

sys.path.append(dirname(dirname(abspath(__file__))))

# 2022-02-06 update to be pure pymysql

class SecretsManagerError(Exception):
    """ SecretsManagerError """


def get_aws_secret_for_section(section):
    if (AWS_SECRET_NAME in section) and (AWS_REGION_NAME) in section:
        secret_name = os.path.expandvars(section[AWS_SECRET_NAME])
        region_name = os.path.expandvars(section[AWS_REGION_NAME])
        logging.debug("secret_name=%s region_name=%s",secret_name, region_name)
        session = boto3.session.Session()
        client = session.client( service_name=SECRETSMANAGER,
                                 region_name=region_name)
        try:
            get_secret_value_response = client.get_secret_value( SecretId=secret_name )
        except ClientError as e:
            raise SecretsManagerError(e)
        secret = json.loads(get_secret_value_response['SecretString'])
        return secret
    return None


def timet_iso(t=time.time()):
    """Report a time_t as an ISO-8601 time format. Defaults to now."""
    return datetime.datetime.now().isoformat()[0:19]


def hostname():
    """Hostname without domain"""
    return socket.gethostname().partition('.')[0]


class DBSQL(ABC):
    def __init__(self, dicts=True, time_zone=None, debug=False):
        self.dicts = dicts
        self.debug = debug

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.conn.close()

    def execute(self, cmd, *args, debug=False, **kwargs):
        """Execute a SQL command and return the the iterator"""
        if self.debug or debug:
            print(f"execute: {cmd}", file=sys.stderr)
            t0 = time.time()
        try:
            res = self.conn.cursor().execute(cmd, *args, **kwargs)
        except (sqlite3.Error, pymysql.MySQLError) as e:
            print(cmd, *args, file=sys.stderr)
            print(e, file=sys.stderr)
            exit(1)
        if self.debug or debug:
            t1 = time.time()
            print(f"time: {t1-t0}", file=sys.stderr)
        return res

    def cursor(self, *args, **kwargs):
        self.conn.ping()        # may need to reconnect
        return self.conn.cursor(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def create_schema(self, schema, *, debug=False):
        """Create the schema if it doesn't exist."""
        c = self.conn.cursor()
        for line in schema.split(";"):
            line = line.strip()
            if len(line) > 0:
                if self.debug or debug:
                    print(f"{line};", file=sys.stderr)
                try:
                    c.execute(line)
                except (sqlite3.Error, pymysql.MySQLError) as e:
                    print("SQL:", line, file=sys.stderr)
                    print("Error:", e, file=sys.stderr)
                    exit(1)

    def execselect(self, sql, vals=()):
        """Execute a SQL query and return the first line"""
        self.conn.ping()
        c = self.conn.cursor()
        c.execute(sql, vals)
        return c.fetchone()

    def close(self):
        self.conn.close()


class DBSqlite3(DBSQL):
    def __init__(self, time_zone=None, fname=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.conn = sqlite3.connect(fname)
            if self.dicts:
                self.conn.row_factory = sqlite3.Row    # user wants dicts

        except sqlite3.OperationalError as e:
            print(f"Cannot open database file: {fname} {e}")
            exit(1)

    def set_cache_bytes(self, b):
        # negative numbers are multiples of 1024
        self.execute(f"PRAGMA cache_size = {-b/1024}")

    # For sqlite3, csfr doesn't need to be a static method, because we don't disconnect from the database
    # Notice that we try to keep API compatiability, but we lose 'auth'. We also change '%s' into '?'
    def csfr(self, auth, cmd, vals=[], *, quiet=True, rowcount=None, time_zone=None,
             get_column_names=None, asDicts=False, debug=False, cache=True):
        assert auth is None
        assert get_column_names is None  # not implemented yet
        cmd = cmd.replace("%s", "?")
        cmd = cmd.replace("INSERT IGNORE", "INSERT OR IGNORE")

        if not quiet:
            print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}")
        if debug or self.debug:
            print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}", file=sys.stderr)

        try:
            c = self.conn.execute(cmd, vals)
        except (sqlite3.OperationalError, sqlite3.InterfaceError) as e:
            print(f"cmd: {cmd}", file=sys.stderr)
            print(f"vals: {vals}", file=sys.stderr)
            print(str(e), file=sys.stderr)
            raise RuntimeError("Invalid SQL")

        verb = cmd.split()[0].upper()
        if verb in ['INSERT', 'DELETE', 'UPDATE']:
            return
        elif verb in ['SELECT', 'DESCRIBE', 'SHOW']:
            return c.fetchall()
        else:
            raise RuntimeError(f"Unknown SQLite3 verb '{verb}'")


class DBMySQLAuth:
    """Class that represents MySQL credentials. Will cache the connection. """

    __slots__ = ['host', 'database', 'user',
                 'password', 'debug', 'dbcache', 'prefix', 'port']

    def __init__(self, *, host, database, user, password, prefix="", debug=False, port=MYSQL_DEFAULT_PORT):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.debug = debug   # enable debugging
        self.dbcache = dict()  # dictionary of cached connections.
        self.prefix = prefix  # available for use
        self.port = port
        if (self.port is None) or (self.port==0):
            self.port = MYSQL_DEFAULT_PORT

    def __eq__(self, other):
        return ((self.host == other.host) and (self.database == other.database)
                and (self.user == other.user) and (self.password == other.password)
                and (self.prefix == other.prefix) and (self.debug == other.debug))

    def __hash__(self):
        return hash(self.host) ^ hash(self.database) ^ hash(self.user) ^ hash(self.password)

    def __repr__(self):
        return f"<DBMySQLAuth host={self.host} database={self.database} user={self.user} prefix={self.prefix} debug={self.debug}>"

    @classmethod
    def GetBashEnvFromFile(this, filename):
        """Loads the bash environment variables specified by 'export NAME=VALUE' into a dictionary and returns it.
        Take whatever variables not in that file from the Linux environment."""
        DB_RE = re.compile("export (.+)=(.+)")
        ret = {}
        if filename is not None:
            with open(filename, "r") as f:
                for line in f:
                    m = DB_RE.search(line.strip())
                    if m:
                        name = m.group(1)
                        val = m.group(2)
                        # Check for quotes
                        if val[0] in "'\"" and val[0] == val[-1]:
                            val = val[1:-1]
                        ret[name] = val
        for name in (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE):
            if name not in ret:
                try:
                    ret[name] = os.environ[name]
                except KeyError:
                    logging.error("%s not in environment not in %s", name, filename)
                    raise
        return ret

    auth_cache = {}

    @classmethod
    def FromBashEnvFile(this, filename, cache=True):
        """Returns a DBMySQLAuth formed by reading MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST and MYSQL_DATABASE envrionemnt variables from a bash script. Caches by default"""
        if cache and filename in this.auth_cache:
            return this.auth_cache[filename]
        env = DBMySQLAuth.GetBashEnvFromFile(filename)
        try:
            auth = DBMySQLAuth(host=env[MYSQL_HOST],
                               user=env[MYSQL_USER],
                               password=env[MYSQL_PASSWORD],
                               database=env[MYSQL_DATABASE])
            if cache:
                this.auth_cache[filename] = auth
            return auth
        except KeyError as e:
            logging.error("filename: %s", filename)
            for var in env:
                logging.error("env[%s] = %s", var, env[var])
            raise e

    @staticmethod
    def FromConfig(section, debug=None):
        """Returns from the section of a config file.
        First checks to see if there is an AWS_SECRET, and uses that if possible.
        Then tries with MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE, which is the standard used from 2005-2023.
        Finally tries with the modern MySQL varialbe names of HOST, USER, PASSWORD and DATABASE.
        Environment variable expansion allows the name or region to be stored in an enviornment variable for multiple deployments.
        """
        if (secret:= get_aws_secret_for_section( section )) is not None:
            logging.debug("retrieved secret for host %s username %s",secret['host'],secret['username'])
            return DBMySQLAuth(host=secret['host'],
                               user=secret['username'],
                               password=secret['password'],
                               database=secret['dbname'],
                               port=int(secret['port']))

        # Look for
        try:
            return DBMySQLAuth(host=section[MYSQL_HOST],
                               user=section[MYSQL_USER],
                               password=section[MYSQL_PASSWORD],
                               database=section.get(MYSQL_DATABASE,None),
                               debug=debug)
        except KeyError:
            pass

        try:
            return DBMySQLAuth(host=section[HOST],
                               user=section[USER],
                               password=section[PASSWORD],
                               database=section.get(DATABASE,None),
                               debug=debug)
        except KeyError:
            pass

        raise KeyError(
            f"config file section must have {MYSQL_HOST}, {MYSQL_USER}, {MYSQL_PASSWORD} and {MYSQL_DATABASE} options in section {section}. Only options found: {list(section.keys())}")

    @staticmethod
    def FromConfigFile(fname, section, *, debug=None, database=None):
        if not os.path.exists(fname):
            raise FileNotFoundError(fname)
        config = configparser.ConfigParser()
        config.read(fname)
        try:
            auth = DBMySQLAuth.FromConfig(config[section], debug=debug)
            if database is not None:
                auth.database = database
            return auth
        except KeyError:
            logging.error("No section %s in file %s", section, fname)
            raise

    @staticmethod
    def FromEnv(debug=None):
        return DBMySQLAuth(host=os.environ[MYSQL_HOST],
                           user=os.environ[MYSQL_USER],
                           password=os.environ[MYSQL_PASSWORD],
                           database=os.environ[MYSQL_DATABASE],
                           debug=debug)

    def cache_store(self, db):
        self.dbcache[(os.getpid(), threading.get_ident())] = db

    def cache_get(self):
        return self.dbcache[(os.getpid(), threading.get_ident())]

    def cache_clear(self):
        try:
            del self.dbcache[(os.getpid(), threading.get_ident())]
        except KeyError:
            pass


RETRIES = 10
RETRY_DELAY_TIME = 1


class DBMySQL(DBSQL):
    """MySQL Database Connection"""

    def __init__(self, auth, time_zone=None, *args, **kwargs):
        super().__init__(*args, **kwargs)  # test
        self.auth = auth
        self.debug = self.debug or auth.debug
        self.conn = pymysql.connect(host=auth.host,
                                    database=auth.database,
                                    user=auth.user,
                                    password=auth.password,
                                    port = auth.port,
                                    autocommit=True)
        if self.debug:
            print(f"Successfully connected to {auth}", file=sys.stderr)

    RETRIES = 10
    RETRY_DELAY_TIME = 1
    IGNORED = 'IGNORED'
    MAX_EXPLAIN_LEN = 1000

    @staticmethod
    def explain(cmd, vals):
        if (not isinstance(vals, list)) and (not isinstance(vals, tuple)) and (vals is not None):
            raise ValueError("vals is type %s expected list" % type(vals))

        def myquote(v):
            if isinstance(v, str):
                return "'" + v + "'"
            return str(v)
        if vals is not None:
            return (cmd % tuple([myquote(v) for v in vals]))[0:DBMySQL.MAX_EXPLAIN_LEN]
        else:
            return cmd

    @staticmethod
    def csfr(auth, cmd, vals=[], *,
             quiet=True, rowcount=None, time_zone=None, setup=None, setup_vals=(),
             get_column_names=None, asDicts=False, debug=False, dry_run=False, cache=True, nolog=[], ignore=[], autocommit=True):
        """Connect, select, fetchall, and retry as necessary.
        :param auth:      - authentication otken
        :param cmd:       - SQL query
        :param vals:      - values for SQL parameters
        :param setup:     - An SQL statement that runs before cmd (typcially setting a variable)
        :param setup_vals: - Values for SQL parameters for setup
        :param time_zone: - if provided, set the session.time_zone to this value
        :param quiet:     - don't print anything
        :param get_column_names: - an array in which to return the column names.
        :param asDict:    - True to return each row as a dictionary
        :param nolog:     - array of error codes that shouldn't be logged with logging.errror
        :param ignore:    - array of error codes to silently ignore.
        """

        for name in DBMySQLAuth.__slots__:
            if not hasattr(auth, name):
                raise TypeError(
                    f"auth (val={auth}) (type {type(auth)}) does not have {name} slot")

        if cmd.count("%s") != len(vals):
            raise ValueError(f"cmd={cmd} cmd.count('%s')={cmd.count('%s')} len(vals)={len(vals)}")

        for i in range(1, DBMySQL.RETRIES):
            try:
                try:
                    db = auth.cache_get()
                except KeyError:
                    if i > 2:
                        logging.warning(f"Reconnecting. i={i}")
                    db = DBMySQL(auth)
                    auth.cache_store(db)
                result = None
                c = db.cursor()
                if autocommit:
                    c.execute('SET autocommit=1')
                if time_zone is not None:
                    # MySQL
                    c.execute(
                        'SET @@session.time_zone = "{}"'.format(time_zone))

                try:
                    if (not quiet) or debug:
                        logging.warning(
                            "quiet:%s debug: %s cmd: %s  vals: %s", quiet, debug, cmd, vals)
                        logging.warning("EXPLAIN:")
                        logging.warning(DBMySQL.explain(cmd, vals))

                    ###
                    ###
                    if dry_run:
                        logging.warning("Would execute: %s,%s", cmd, vals)
                        return None

                    # If there are multiple queries, execute them all.
                    # Hopefully there is no semi-colon in a quoted string.
                    if setup is not None:
                        c.execute(setup, setup_vals)
                    t0 = time.time()
                    c.execute(cmd, vals)
                    t1 = time.time()
                    ###
                    ###

                    if debug:
                        logging.warning("TIME TO EXECUTE: %s", t1 - t0)

                    if (rowcount is not None) and (c.rowcount != rowcount):
                        raise RuntimeError(
                            f"{cmd} {vals} expected rowcount={rowcount} != {c.rowcount}")

                except (pymysql.ProgrammingError, pymysql.InternalError,
                        pymysql.IntegrityError, pymysql.InterfaceError) as e:
                    if e.args[0] in ignore:
                        return DBMySQL.IGNORED
                    if e.args[0] not in nolog:
                        logging.error("setup: %s", setup)
                        logging.error("setup_vals: %s", setup_vals)
                        logging.error("cmd: %s", cmd)
                        logging.error("vals: %s", vals)
                        logging.error("explained: %s ", DBMySQL.explain(cmd, vals))
                        logging.error("auth: %s", auth)
                        logging.error(str(e))
                    raise

                except TypeError as e:
                    logging.error(f"TYPE ERROR: cmd:{cmd} vals:{vals} {e}")
                    if 'not enough' in str(e):
                        logging.error(
                            "Count of parameters: %s  count of values: %s", cmd.count("%"), len(vals))
                    raise e

                verb = cmd.split()[0].upper()
                if verb in ['SELECT', 'DESCRIBE', 'SHOW']:
                    result = c.fetchall()
                    if asDicts and get_column_names is None:
                        get_column_names = []
                    if get_column_names is not None:
                        get_column_names.clear()
                        for (name, type_code, display_size, internal_size, precision, scale, null_ok) in c.description:
                            get_column_names.append(name)
                    if asDicts:
                        result = [OrderedDict(zip(get_column_names, row))
                                  for row in result]
                elif verb in ['INSERT']:
                    result = c.lastrowid
                elif verb in ['UPDATE', 'DELETE', 'UPDATE']:
                    result = c.rowcount
                c.close()  # close the cursor
                if debug:
                    logging.warning(
                        " result=%s", json.dumps(result, default=str))
                if i > 2:
                    logging.warning(f"Success with i={i}")
                return result
            except (pymysql.OperationalError, pymysql.InternalError) as e:
                # These errors we do not retry
                logging.error("%s %s in CMD: %s  explained: %s",
                              e.args[0], e.args[1], cmd, DBMySQL.explain(cmd, vals))
                if e.args[0] not in ERRORS_NO_RETRY:
                    raise
                logging.warning(
                    f"OperationalError. RETRYING {i}/{DBMySQL.RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
                pass
            except BlockingIOError as e:
                if i > 1:
                    logging.warning(e)
                    logging.warning(
                        f"BlockingIOError. RETRYING {i}/{DBMySQL.RETRIES}: {cmd} {vals} ")
                auth.cache_clear()
                pass
            time.sleep(RETRY_DELAY_TIME)
        raise RuntimeError("Retries Exceeded")

    @staticmethod
    def table_columns(auth, table_name):
        """Return a dictionary of the schema. This should probably be upgraded to return the ctools schema"""
        return [row[0] for row in DBMySQL.csfr(auth, "describe " + table_name)]
