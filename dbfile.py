#
# Methods that return File(pathid,dirname,filename) for searches
#

import datetime
import time
import os
import logging

CACHE_SIZE = 2000000
SQL_SET_CACHE = "PRAGMA cache_size = {};".format(CACHE_SIZE)

def timet_iso(t=time.time()):
    """Report a time_t as an ISO-8601 time format. Defaults to now."""
    return datetime.datetime.now().isoformat()[0:19]

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
        self.host = host
        self.database = database
        self.user=user
        self.password = password


RETRIES = 10
RETRY_DELAY_TIME = 1
class DBMySQL(DBSQL):
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

        
    @staticmethod
    def csfr(auth,cmd,vals=None,quiet=True):
        """Connect, select, fetchall, and retry as necessary"""
        try:
            import mysql.connector.errors as errors
        except ImportError as e:
            import pymysql.err as errors
        for i in range(1,RETRIES):
            try:
                db = DBMySQL(auth)
                result = None
                c = db.cursor()
                c.execute('set autocommit=1')
                try:
                    if quiet==False:
                        print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}")
                    c.execute(cmd,vals)
                except errors.ProgrammingError as e:
                    logging.error("cmd: "+str(cmd))
                    logging.error("vals: "+str(vals))
                    logging.error(str(e))
                    raise e
                if cmd.upper().startswith("SELECT"):
                    result = c.fetchall()
                c.close()  # close the cursor
                db.close() # close the connection
                return result
            except errors.InterfaceError as e:
                logging.error(e)
                logging.error(f"PID{os.getpid()}: NO RESULT SET??? RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                pass
            except errors.OperationalError as e:
                logging.error(e)
                logging.error(f"PID{os.getpid()}: OPERATIONAL ERROR??? RETRYING {i}/{RETRIES}: {cmd} {vals} ")
                pass
            time.sleep(RETRY_DELAY_TIME)
        raise RuntimeError("Retries Exceeded")


