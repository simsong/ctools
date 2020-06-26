#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test the Census ETL schema package

import os
import sys

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))

import ctools
import ctools.schema as schema

from ctools.schema import valid_sql_name,unquote,sql_parse_create,decode_vtype
from ctools.schema.table import Table
from ctools.schema.schema import Schema
from ctools.schema.variable import Variable

def test_valid_sql_name():
    assert valid_sql_name("MDF_TabulationGeography")==True
    assert valid_sql_name("CEFVW_PP10_OP")==True

#def test_TYPE_WIDTH_RE():
#    m = TYPE_WIDTH_RE.search("VARCHAR(20)")
#    assert m is not None
#    assert m.group('name')=='VARCHAR'
#    assert m.group('width')=='20'
#
#    m = TYPE_WIDTH_RE.search("VARCHAR2")
#    assert m is not None
#    assert m.group('name')=='VARCHAR2'
#    assert m.group('width') is None

def test_decode_vtype():
    print("*** schema: ",schema)
    assert decode_vtype("VARCHAR(20)") == (schema.TYPE_VARCHAR, 20)
    assert decode_vtype("VARCHAR2") == (schema.TYPE_VARCHAR, schema.DEFAULT_VARIABLE_WIDTH)

def test_unquote():
    assert unquote("'this'") == "this"
    assert unquote("'this'") == "this"
    assert unquote("'this'") == "this"
    assert unquote("‘this’") == "this"
    assert unquote("“this”") == "this"
    assert unquote("that")   == "that"
    

SQL_CREATE1="""    CREATE TABLE output (
    INTEGER StudentNumber,
    VARCHAR CourseNumber,
    VARCHAR CourseName
    );
"""

def test_sql_parse_create():
    sql = sql_parse_create(SQL_CREATE1)
    assert sql['table']=='output'
    assert sql['cols'][0]=={'vtype':'INTEGER','name':'StudentNumber'}
    assert sql['cols'][1]=={'vtype':'VARCHAR','name':'CourseNumber'}
    assert sql['cols'][2]=={'vtype':'VARCHAR','name':'CourseName'}
