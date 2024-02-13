#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test the Census ETL schema package

from ctools.schema import valid_sql_name, unquote, sql_parse_create, decode_vtype
from ctools.schema.variable import Variable
from ctools.schema.schema import Schema
from ctools.schema.table import Table
import ctools.schema as schema
import os
import sys

from os.path import abspath
from os.path import dirname

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))


# We should try parsing this too.
SCHEMA_TEST = """CREATE TABLE students (
   name VARCHAR -- ,
   age INTEGER --
);"""

DATALINE1 = "jack10"
DATALINE2 = "mary25"


def test_Table():
    s = Schema()
    t = Table(name="students")
    s.add_table(t)
    name = Variable(name="name", vtype='VARCHAR(4)',
                    column=0, width=4, start=1, end=4)
    assert(name.python_type == str)
    age = Variable(name="age", vtype='INTEGER(2)',
                   column=4, width=2, start=5, end=6)
    t.add_variable(name)
    t.add_variable(age)
    assert name.column == 0
    assert name.width == 4
    assert age.column == 4
    assert age.width == 2

    assert t.get_variable("name") == name
    assert t.get_variable("age") == age
    assert list(t.vars()) == [name, age]

    # Try SQL conversion
    sql = t.sql_schema()
    assert "CREATE TABLE students" in sql
    assert "name VARCHAR" in sql
    assert "age INTEGER" in sql

    # See if the parsers work
    data = t.parse_line_to_dict(DATALINE1)
    assert data == {"name": "jack", "age": 10}
    assert t.parse_line_to_row(DATALINE1) == ["jack", 10]

    # Add a second table
    t = Table(name="parents")
    s.add_table(t)
    t.add_variable(Variable(name="parent", vtype=schema.TYPE_VARCHAR))

    # See if adding a recode works
    s.add_recode("recode1", schema.TYPE_VARCHAR,
                 "parents[studentname]=students[name]")
    s.add_recode("recode2", schema.TYPE_INTEGER, "parents[three]=3")
    s.add_recode("recode3", schema.TYPE_VARCHAR,
                 "parents[student_initials]=students[name][0:1]")
    s.compile_recodes()

    # verify that the parents table now has a student name variable of the correct type
    assert s.get_table("parents").get_variable(
        "studentname").name == "studentname"
    assert s.get_table("parents").get_variable(
        "studentname").vtype == schema.TYPE_VARCHAR

    # Let's load a line of data for recoding
    s.recode_load_data("students", data)

    # Now record a parent record
    parent = {"name": "xxxx"}
    s.recode_execute("parents", parent)

    # Now make sure that the recoded data is there
    assert parent['studentname'] == 'jack'
    assert parent['three'] == 3
    assert parent['student_initials'] == 'j'


SQL_CREATE1 = """    CREATE TABLE output (
    INTEGER StudentNumber,
    VARCHAR CourseNumber,
    VARCHAR CourseName
    );
"""


def test_sql_parse_create():
    sql = sql_parse_create(SQL_CREATE1)
    assert sql['table'] == 'output'
    assert sql['cols'][0] == {'vtype': 'INTEGER', 'name': 'StudentNumber'}
    assert sql['cols'][1] == {'vtype': 'VARCHAR', 'name': 'CourseNumber'}
    assert sql['cols'][2] == {'vtype': 'VARCHAR', 'name': 'CourseName'}
