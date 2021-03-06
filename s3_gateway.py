#!/usr/bin/python3
# -*- mode: python -*-


"""
s3_gateway: 
bottle/boto3 interface to view an s3 bucket in a web browser.
Currently not operational; based on operational code elsewhere.
Being refactored into public code and prvate code.

"""

# disable PKI warnings
# https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
import urllib3
urllib3.disable_warnings()

import os
import sys
import socket
import json
import time
import logging
import datetime
import time
import webmaint
import tempfile
import bottle
import subprocess
import io
import mimetypes
import pprint
import shutil
import gzip
import pytz

from bottle import request,response

import das_graphql
import ctools.dbfile as dbfile
import ctools.env    as env
import ctools.tydoc  as tydoc
import ctools.s3     as s3

import zipfile

from auth import get_auth
from zipfile import ZipFile

__version__="0.1.0"

LOG_BUCKET = 'uscb-decennial-ite-das-logs'
ITE_BUCKET = 'uscb-decennial-ite-das'
TMP_DIR    = '/mnt2/tmp'

MELLON_UID = 'MELLON_uid'
LOGFILE_LOCATION = "rpc/upload/logs/"

EASTERN_TIME = pytz.timezone('US/Eastern')

mimetypes.init()
mimetypes.add_type('application/sas',     '.sas')
mimetypes.add_type('application/x-hdf',    '.h5')
mimetypes.add_type('application/zip',      '.gz')
mimetypes.add_type('application/zip',  '.txt.gz')
mimetypes.add_type('text/plain', '.txt.head.txt')
mimetypes.add_type('text/plain', '.txt.tail.txt')
mimetypes.add_type('text/plain', '.log')

filetypes_view_in_browser = set(['.txt','.log'])

def s3_is_integer(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def get_cb_das_members():
    """ Returns a list of jbid members """
    return sorted(das_graphql.get_members('CB-DAS'))

def s3_list_zip_contents(s3_url):
    """ Returns a list of files in the given S3 zip file """
    s3File = s3.S3File(s3_url)
    s3Zip = zipfile.ZipFile(s3File, mode='r', allowZip64=True)
    return s3Zip.namelist() 

def s3_log_zip_contents(archive):
    return s3_app_gen_zip_contents("app/logs/zip/download/", LOG_BUCKET, archive)
    
def s3_app_zip_contents(environ, archive):
    f = io.StringIO()    

    APPROVED_USERS = get_cb_das_members()
   
    if MELLON_UID not in environ:
        f.write("Not running under MELLON")
        return f.getvalue()
        
    if environ[MELLON_UID] not in APPROVED_USERS:
        f.write(environ[MELLON_UID] + " is not authenticated")
        return f.getvalue()

    return s3_app_gen_zip_contents("app/s3/zip/download/", ITE_BUCKET, archive)


def s3_app_gen_zip_contents(download_api, bucket, archive):
    import boto3

    f = io.StringIO()    

    suffix = os.path.dirname(archive)
    
    f.write(f"<h3>{archive}</h3>")
    
    s3client = boto3.client('s3')

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tempdirname:
        try:                
            if archive.endswith("gz"):
                response.content_type = 'text/plain'
                
                fname = os.path.join(tempdirname, "download.gz")
                s3client.download_file(bucket, archive, fname)
                
                try:
                    with gzip.open(fname, 'r') as f:
                        return f.read()
                except gzip.BadGzipFile as e:
                    pprint.pformat(e, indent=4)
                    
            else:
                response.content_type = 'text/html'

                fname = os.path.join(tempdirname, "download.zip")
                s3client.download_file(bucket, archive, fname)

                if zipfile.is_zipfile(fname):
                    zip = ZipFile(fname, 'r')
                    f.write('<br/>'.join(['<a href="%s%s%s/%s">%s</a>' % (webmaint.SERVER_BASE_HREF, download_api, archive, file, file) for file in zip.namelist()]))
                else:
                    f.write(f"<h3>Not a Zip File ({fname})</h3>")
                
        except FileNotFoundError as e:
            f.write(f"File not found: s3://{bucket}/{archive}")

    return f.getvalue()


"""
Extract and Download a file from a zip file
"""
def s3_log_zip_download(archive, path):
    return s3_gen_zip_download(LOG_BUCKET, archive, path)


def s3_app_zip_download(environ, archive, path):
    APPROVED_USERS = get_cb_das_members()

    if MELLON_UID not in environ:
        return "Not running under MELLON"

    if environ[MELLON_UID] not in APPROVED_USERS:
        return environ[MELLON_UID] + " is not authenticated"

    return s3_gen_zip_download(ITE_BUCKET, archive, path)


def s3_gen_zip_download(bucket, archive, path):
    import boto3

    s3client = boto3.client('s3')

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tempdirname:
        try:
            if archive.endswith("gz") or archive.endswith("zip"):
                fname = os.path.join(tempdirname, "download.zip")
                s3client.download_file(bucket, archive, fname)

                if zipfile.is_zipfile(fname):
                    zip = ZipFile(fname, 'r')
                    zip.extract(path, tempdirname, pwd=None)
                    ename = os.path.join(tempdirname, path)

                    response.set_header('Content-Disposition', f'attachment; filename="{path}"')

                    try:
                        response.content_type = mimetypes.guess_type(ename)[0]
                    except:
                        response.content_type = 'application/octet-stream'

                    return open(ename, "r")

        except FileNotFoundError as e:
            return f"File not found: s3://{bucket}/{archive}"

"""
Download a file from an S3 bucket
"""
def s3_log_download(path):
    return s3_gen_download(LOG_BUCKET, path)

def s3_app_download(environ, path):
    """Used to access anything under $DAS_S3ROOT/download/.
    Verify that the user is approved, and then just return the data.
    """

    APPROVED_USERS = get_cb_das_members()

    if MELLON_UID not in environ:
        return "Not running under MELLON"

    if environ[MELLON_UID] not in APPROVED_USERS:
        return environ[MELLON_UID] + " is not authenticated"


    return s3_gen_download(ITE_BUCKET, path)


def s3_gen_download(bucket, path):
    import boto3
    import botocore
    s3client = boto3.client('s3')

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tempdirname:
        try:
            fname = os.path.join(tempdirname, "download")
            s3client.download_file(bucket, path, fname)

            if os.path.splitext(path)[1] not in filetypes_view_in_browser:
                response.set_header('Content-Disposition', f'attachment; filename="{path}"')

            try:
                response.content_type = mimetypes.guess_type(fname)[0]
            except:
                response.content_type = 'application/octet-stream'

            return open(fname, "r")

        except (FileNotFoundError,botocore.exceptions.ClientError) as e:
            return f"File not found: s3://{bucket}/{path}"



"""
Find a file in directory
"""
def s3_log_find_in_dir(path, pattern):
    return s3_gen_find_in_dir("app/logs/zip/contents/", LOG_BUCKET, path, pattern)


def s3_app_find_in_dir(environ, path, pattern):
    f = io.StringIO()
    
    APPROVED_USERS = get_cb_das_members()
    
    if MELLON_UID not in environ:
        f.write("Not running under MELLON")
        return f.getvalue()

    if environ[MELLON_UID] not in APPROVED_USERS:
        f.write(environ[MELLON_UID] + " is not authenticated")
        return f.getvalue()

    if not path.endswith("/"):
        path += "/"

    return s3_gen_find_in_dir("app/s3/zip/contents/", ITE_BUCKET, path, pattern)


def s3_gen_find_in_dir(contents_api, bucket, path, pattern):
    import boto3
    
    f = io.StringIO()

    s3client = boto3.client('s3')

    paginator = s3client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/')

    try:
        for page in pages:
            if ('Contents' in page):
                for obj in page['Contents']:
                    if ('Key' in obj and pattern in obj['Key']):
                        name = obj['Key'].split('/')[-1]
                        f.write(f"<a href='{webmaint.SERVER_BASE_HREF}{contents_api}{path}{name}' target='_blank'>{name}</a><br/>\n")

    except:
        f.write(f"Something went wrong at {path}<br/>\n")

    return f.getvalue()

def s3_gen_get_name_in_dir(bucket, path, pattern):
    import boto3

    s3client = boto3.client('s3')

    paginator = s3client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/')

    try:
        for page in pages:
            if ('Contents' in page):
                for obj in page['Contents']:
                    if ('Key' in obj and pattern in obj['Key']):
                        name = obj['Key'].split('/')[-1]
                        return name

    except:
        return None

"""
find a file in a zip file
"""
def s3_log_find_in_zip(path, zip_pattern, pattern):
    return s3_gen_find_in_zip("app/logs/zip/download/", LOG_BUCKET, path, zip_pattern, pattern)


def s3_app_find_in_zip(environ, path, zip_pattern, pattern):
    f = io.StringIO()
    
    APPROVED_USERS = get_cb_das_members()
    
    if MELLON_UID not in environ:
        f.write("Not running under MELLON")
        return f.getvalue()

    if environ[MELLON_UID] not in APPROVED_USERS:
        f.write(environ[MELLON_UID] + " is not authenticated")
        return f.getvalue()

    if not path.endswith("/"):
        path += "/"

    return s3_gen_find_in_zip("app/s3/zip/download/", ITE_BUCKET, path, zip_pattern, pattern)


def s3_gen_find_in_zip(download_api, bucket, path, zip_pattern, pattern):
    import boto3
    
    f = io.StringIO()

    s3client = boto3.client('s3')

    paginator = s3client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/')

    try:
        for page in pages:
            if ('Contents' in page):
                for obj in page['Contents']:
                    if ('Key' in obj and zip_pattern in obj['Key']):
                        name  = obj['Key'].split('/')[-1]
                        with tempfile.TemporaryDirectory(dir=TMP_DIR) as tempdirname:
                            fname = os.path.join(tempdirname, name)
                            zname = f"{path}{name}"
                            s3client.download_file(bucket, zname, fname)
                            
                            if zipfile.is_zipfile(fname):
                                zip = ZipFile(fname, 'r')
                                for file in zip.namelist():
                                    if (pattern in file):
                                        f.write('<a href="%s%s%s/%s">%s</a><br/>' % (webmaint.SERVER_BASE_HREF, download_api, obj['Key'], file, file))
                            
    except:
        f.write(f"Something went wrong at {path}<br/>\n")

    return f.getvalue()

# returns a list of strings containing the contents of the path
def s3_get_contents_list(bucket, path):
    import boto3

    contents = []

    s3client = boto3.client('s3')

    paginator = s3client.get_paginator('list_objects_v2')
    
    if path == '/':
        # Get Directories
        dir_pages = paginator.paginate(Bucket=bucket, Delimiter='/', PaginationConfig={'MaxItems': 100})

        if dir_pages:
            for dir in dir_pages.search('CommonPrefixes'):
                if dir:
                    contents.append(dir.get('Prefix').replace(path, ''))
    else:
        # Get Directories
        dir_pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/', PaginationConfig={'MaxItems': 100})
        
        if dir_pages:
            for dir in dir_pages.search('CommonPrefixes'):
                if dir:
                    contents.append(dir.get('Prefix').replace(path, ''))

        # Get Files
        pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/')
        
        objs = []
        
        if pages:
            # cache pages due to 1000 object limit on aws api
            for page in pages:
                if ('Contents' in page):
                    for obj in page['Contents']:
                        objs.append(obj)
        else:
            return contents
        
        for obj in objs:
            name = obj['Key'].split('/')[-1]
            contents.append(name)
        
    return contents

def s3_dir(environ, path):
    f = io.StringIO()

    APPROVED_USERS = get_cb_das_members()
    
    if MELLON_UID not in environ:
        f.write("Not running under MELLON")
        return f.getvalue()

    if environ[MELLON_UID] not in APPROVED_USERS:
        f.write(environ[MELLON_UID] + " is not authenticated")
        return f.getvalue()

    if path:
        if not path.endswith("/"):
            path += "/"
    else:
        path = "/"

    return s3_gen("app/s3/dir/", "app/s3/zip/contents/", "app/s3/download/", ITE_BUCKET, path)


def s3_gen(api, contents_api, download_api, bucket, path):
    import boto3

    f = io.StringIO()

    f.write(f"<h1>{path}</h1>\n")

    s3client = boto3.client('s3')

    paginator = s3client.get_paginator('list_objects_v2')
    
    if path == '/':
        # Get Directories
        dir_pages = paginator.paginate(Bucket=bucket, Delimiter='/', PaginationConfig={'MaxItems': 100})

        if dir_pages:
            for dir in dir_pages.search('CommonPrefixes'):
                if dir:
                    f.write(f"<a href='{webmaint.SERVER_BASE_HREF}{api}{dir.get('Prefix')}'>PRE {dir.get('Prefix').replace(path, '')}</a><br/>\n")
    else:
        # Get Directories
        dir_pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/', PaginationConfig={'MaxItems': 100})
        
        if dir_pages:
            for dir in dir_pages.search('CommonPrefixes'):
                if dir:
                    f.write(f"<a href='{webmaint.SERVER_BASE_HREF}{api}{dir.get('Prefix')}'>PRE {dir.get('Prefix').replace(path, '')}</a><br/>\n")


        # Get Files
        pages = paginator.paginate(Bucket=bucket, Prefix=path, Delimiter='/')
        
        objs = []
        
        if pages:
            # cache pages due to 1000 object limit on aws api
            for page in pages:
                if ('Contents' in page):
                    for obj in page['Contents']:
                        objs.append(obj)
        else:
            f.write(f"Nothing found at {path}<br/>")
            return f.getvalue()
        
        try:
            
            f.write("<table>\n")
            
            for obj in objs:
                name = obj['Key'].split('/')[-1]
                size = obj['Size']
                time = obj['LastModified'].astimezone(EASTERN_TIME)                

                # format size by: adding commas and right justifying
                # format date by: changing to eastern timezone

                if name.endswith("gz") or name.endswith("zip"):
                    f.write(f"<tr><td><a href='{webmaint.SERVER_BASE_HREF}{contents_api}{path}{name}'>{name}</a></td><td style='text-align:right;'> {size:,}</td><td>{time}</td></tr>\n")
                else:
                    f.write(f"<tr><td><a href='{webmaint.SERVER_BASE_HREF}{download_api}{path}{name}'>{name}</a></td><td style='text-align:right;'> {size:,}</td><td>{time}</td></tr>\n")
                
            f.write("</table>\n")
        
        except:
            f.write(f"Something went wrong at {path}<br/>\n")
            
    return f.getvalue()
    

def s3_app(environ, auth, bucket, path):
    return "foo"
    APPROVED_USERS = get_cb_das_members()
    
    if MELLON_UID not in environ:
        return "Not running under MELLON"
        
    if environ[MELLON_UID] not in APPROVED_USERS:
        return environ[MELLON_UID] + " is not authenticated"
    
    import boto3
    s3client = boto3.client('s3')

    """
    Fetching a file
    """
    if not path.endswith("/"):
        with tempfile.TemporaryDirectory(dir=TMP_DIR) as tempdirname:
            try:
                if path.endswith("gz") or path.endswith("zip"):
                    fname = os.path.join(tempdirname, "download.zip")
                    s3client.download_file(bucket, path, fname)
                    response.content_type = 'text/html'

                    if zipfile.is_zipfile(fname):
                        zip = ZipFile(fname, 'r')
                        f.write('<br/>'.join(['<a href="%sapp/s3/zip/download/%s/%s">%s</a>' % (webmaint.SERVER_BASE_HREF, archive, file, file) for file in zip.namelist()]))
                    else:
                        f.write("<h3>Not a Zip File</h3>")
                    
                    return f.getvalue()
                    
                    
                if path.lower().endswith(".pdf"):
                    fname = os.path.join(tempdirname, "download.pdf")
                    s3client.download_file(bucket, path, fname)
                    response.content_type = 'application/pdf'
                    return open(fname, "rb")

                if path.lower().endswith(".txt") or path.lower().endswith(".out"):
                    fname = os.path.join(tempdirname, "download.txt")
                    s3client.download_file(bucket, path, fname)
                    response.content_type = 'text/plain'
                    return open(fname, "r")

                if path.lower().endswith(".sas"):
                    fname = os.path.join(tempdirname, "download.sas")
                    s3client.download_file(bucket, path, fname)
                    response.content_type = 'text/plain'
                    return open(fname, "r")

                """
                Unknown Filetype
                """
                fname = os.path.join(tempdirname, "download.unk")
                s3client.download_file(bucket, path, fname)
                response.set_header('Content-Disposition', f'attachment; filename="{path}"')

                try:
                    response.content_type = mimetypes.guess_type(fname)[0]
                except:
                    response.content_type = 'application/octet-stream'

                return open(fname, "rb")

            except FileNotFoundError as e:
                return f"File not found: s3://{bucket}/{path}"
                
    """
    Fetching Directory Contents
    """
    f = io.StringIO()

    f.write("<html><body>")

    f.write(f"<h1>{path}</h1>\n")

    # setup paginator due to 1000 object limit on aws api
    paginator = s3client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=path)

    if pages:
        try:
            objs = []

            # cache pages due to 1000 object limit on aws api
            for page in pages:
                for obj in page['Contents']:
                    objs.append(obj)

        
            f.write("<ul>\n")
            for obj in objs:
                if 'Prefix' in obj:
                    suffix = obj['Prefix'].split("/")[-2]
                    f.write(f"<li><a href='{request.url}/{suffix}'>{suffix}</a></li>\n")
            f.write("</ul>\n")
            
            f.write("<table>\n")
            for obj in objs:
                if 'Prefix' not in obj:
                    name = obj['Key'].split('/')[-1]
                    f.write(f"<tr><td><a href='{request.url}{name}'>{name}</a></td><td> {obj['Size']}</td><td>{obj['LastModified']}</td></tr>\n")
            f.write("</table>\n")

        except:
            f.write(f"Trouble reading {path}<br/>")
    else:
        f.write(f"Nothing found at {path}<br/>")

    f.write("</body></html>")
    
    return f.getvalue()



if __name__=="__main__":
    import argparse
    
    # from ctools.lock import lock_script
    # lock_script()
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description="""This is the testing program for the gateway that allows S3 files to be accessed from the dashboard. If given a prefix, it will display the HTML UI for choosing a file. Otherwise it will provide the file's contents.""")
    parser.add_argument("--quiet",  action='store_true')
    parser.add_argument("--path",   default=LOGFILE_LOCATION, help='path within the bucket to access. Do not include leading slash')
    parser.add_argument("--bucket", default=ITE_BUCKET, help='which bucket to use.')
    parser.add_argument("--zip_pattern")
    parser.add_argument("--log_cluster")
    parser.add_argument("--log_application")
    parser.add_argument("--pattern")
    parser.add_argument('--dump',help='just dump the file',action='store_true')
    parser.add_argument("--whoapproved", action='store_true', help='print a list of who is approved')
    
    args = parser.parse_args()
    auth = get_auth('dbreader')

    if args.whoapproved:
        print("get_cb_das_members: ",get_cb_das_members())
        exit(0)

    if args.dump:
        f = s3_gen_download(args.bucket, args.path)
        print(f.read())
        exit(0)


    if args.zip_pattern:
        if args.pattern:
            ret = s3_gen_find_in_zip("app/download/", args.bucket, args.path, args.zip_pattern, args.pattern)
        else:
            ret = s3_gen_find_in_dir("app/contents/", args.bucket, args.path, args.zip_pattern)
    else:
        ret = s3_gen("app/dir/", "app/contents/", "app/download/", args.bucket, args.path)

    pprint.pprint(ret)
