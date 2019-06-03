#
# Methods that return File(pathid,dirname,filename) for searches
#

import datetime
import time
import os

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


class DBMySQL(DBSQL):
    def __init__(self,auth):
        try:
            import mysql.connector as mysql
            self.conn = mysql.connect(host=auth.host,
                                      database=auth.database,
                                      user=auth.user,
                                      password=auth.password)
            self.dbs.cursor().execute('SET @@session.time_zone = "America/New_York"') # Census standard
            self.dbs.cursor().execute('SET autocommit = 1') # autocommit

        except ImportError as e:
            print(f"Please install MySQL connector with 'conda install mysql-connector-python'")
            exit(1)
        
    @staticmethod
    RETRIES = 10
    RETRY_DELAY_TIME = 1
    def csfr(auth,cmd,vals=None,quiet=False):
        """Connect, select, fetchall, and retry as necessary"""
        import mysql.connector.errors
        for i in range(1,self.RETRIES):
            try:
                db = DBMySQL(auth)
                db.connect()
                result = None
                c = db.cursor()
                try:
                    logging.info(f"PID{os.getpid()}: {cmd} {vals}")
                    if quiet==False:
                        print(f"PID{os.getpid()}: cmd:{cmd} vals:{vals}")
                    c.execute(cmd,vals)
                except mysql.connector.errors.ProgrammingError as e:
                    logging.error("cmd: "+str(cmd))
                    logging.error("vals: "+str(vals))
                    logging.error(str(e))
                    raise e
                if cmd.upper().startswith("SELECT"):
                    result = c.fetchall()
                c.close()       # close the cursor
                db.close() # close the connection
                return result
            except mysql.connector.errors.InterfaceError as e:
                logging.error(e)
                logging.error(f"PID{os.getpid()}: NO RESULT SET??? RETRYING {i}/{self.RETRIES}: {cmd} {vals} ")
                pass
            except mysql.connector.errors.OperationalError as e:
                logging.error(e)
                logging.error(f"PID{os.getpid()}: OPERATIONAL ERROR??? RETRYING {i}/{self.RETRIES}: {cmd} {vals} ")
                pass
            time.sleep(self.RETRY_DELAY_TIME)
        raise e

