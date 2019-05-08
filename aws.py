import json
import requests
import os
import subprocess


################################################################
###
### Proxy Control
###
### Please create an environment variable called BCC_PROXY with the IP address of your proxy server for the EMR commands
###
################################################################

HTTP_PROXY='HTTP_PROXY'
HTTPS_PROXY='HTTPS_PROXY'
BCC_HTTP_PROXY='BCC_HTTP_PROXY'
BCC_HTTPS_PROXY='BCC_HTTPS_PROXY'
NO_PROXY='NO_PROXY'

class Proxy:    
    def __init__(self):
        pass

    def __enter__(self):
        if BCC_HTTP_PROXY in os.environ:
            os.environ[HTTP_PROXY] = os.environ[BCC_HTTP_PROXY]
        if BCC_HTTPS_PROXY in os.environ:
            os.environ[HTTPS_PROXY] = os.environ[BCC_HTTPS_PROXY]
        return self

    def __exit__(self, *args):
        if HTTP_PROXY in os.environ:
            del os.environ[HTTP_PROXY]
        if HTTPS_PROXY in os.environ:
            del os.environ[HTTPS_PROXY]


def show_credentials():
    """This is mostly for debugging"""
    subprocess.call(['printenv'])
    subprocess.call(['aws','configure','list'])


def instance_identity():
    return json.loads(requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document'))


def ami_id():
    r = requests.get('http://169.254.169.254/latest/meta-data/ami-id')
    return r.text


if __name__=="__main__":
    print("AWS Info:")
    doc = instance_identity()
    for (k,v) in doc.items():
        print("{}: {}".format(k,v))
    print("AMI ID: {}".format(ami_id()))
