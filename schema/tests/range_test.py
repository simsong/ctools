#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test the Census ETL schema package

from ctools.schema.range import Range
import os
import sys
from os.path import dirname
from os.path import abspath

sys.path.append(dirname(dirname(dirname(dirname(abspath(__file__))))))


def test_range_funcs():
    r1 = Range(1, 1)
    r2 = Range(1, 1)
    assert r1 == r2
    r3 = Range(2, 2)
    assert r1 < r3


def test_combine_ranges():
    r1 = Range(1, 2)
    r2 = Range(2, 4)
    r3 = Range(10, 12)
    l1 = [r1, r2, r3]
    assert Range.combine_ranges([r1, r2]) == [Range(1, 4)]
    assert Range.combine_ranges([r1, r2, r3]) == [Range(1, 4), Range(10, 12)]


def test_parse():
    res = Range.extract_range_and_desc("1 hello", hardfail=True)
    assert type(res) == Range
    assert res.a == '1'
    assert res.b == '1'
    assert res.desc == "hello"

    assert Range.extract_range_and_desc(
        "1 hello", python_type=int, hardfail=True) == Range(1, 1, "hello")
    assert Range.extract_range_and_desc(
        "1-2 hello", python_type=int, hardfail=True) == Range(1, 2, "hello")
    assert Range.extract_range_and_desc(
        "1-2 = hello", python_type=int, hardfail=True) == Range(1, 2, "hello")
    assert Range.extract_range_and_desc(
        "1-2 = (hello)", python_type=int, hardfail=True) == Range(1, 2, "hello")

    assert Range.extract_range_and_desc(
        "1 hello 3-4", python_type=int, hardfail=True) == Range(1, 1, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1 (hello 3-4)", python_type=int, hardfail=True) == Range(1, 1, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1 = hello 3-4", python_type=int, hardfail=True) == Range(1, 1, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1 = (hello 3-4)", python_type=int, hardfail=True) == Range(1, 1, "hello 3-4")

    assert Range.extract_range_and_desc(
        "1-2 hello 3-4", python_type=int, hardfail=True) == Range(1, 2, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1-2 (hello 3-4)", python_type=int, hardfail=True) == Range(1, 2, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1-2 = hello 3-4", python_type=int, hardfail=True) == Range(1, 2, "hello 3-4")
    assert Range.extract_range_and_desc(
        "1-2 = (hello 3-4)", python_type=int, hardfail=True) == Range(1, 2, "hello 3-4")

    assert Range.extract_range_and_desc(
        "      1 = hello 3-4", python_type=int, hardfail=True) == Range(1, 1, "hello 3-4")

    # A few descriptions that we don't want to parse as Ranges
    assert Range.extract_range_and_desc(
        "Up to 22 values", python_type=int, hardfail=False) == None
    assert Range.extract_range_and_desc(
        "Fips State Code (The legal values for this file are 01-02, 04-06)", python_type=int, hardfail=False) == None
