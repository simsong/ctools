#
# Methods that return File(pathid,dirname,filename) for searches
#

import datetime
import time
import os
import sqlite3

CACHE_SIZE = 2000000
SQL_SET_CACHE = "PRAGMA cache_size = {};".format(CACHE_SIZE)

def timet_iso(t=time.time()):
    """Report a time_t as an ISO-8601 time format. Defaults to now."""
    return datetime.datetime.now().isoformat()[0:19]

class DBSQL:
    def __init__(self,*,fname):
        try:
            self.conn = sqlite3.connect(fname)
        except sqlite3.OperationalError as e:
            print(f"Cannot open database file: {fname}")
            exit(1)
        
    def __enter__(self):
        return self

    def __exit__(self,a,b,c):
        self.conn.close()

    def create_schema(self,schema):
        """Create the schema if it doesn't exist."""
        c = self.conn.cursor()
        for line in schema.split(";"):
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
