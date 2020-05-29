import json
import os
import subprocess
import urllib.request


################################################################
###
### Proxy Control
###
### Please create an environment variable called BCC_PROXY with the IP address of your proxy server for the EMR commands
###
################################################################

HTTP_PROXY='HTTP_PROXY'
HTTPS_PROXY='HTTPS_PROXY'
BCC_HTTP_PROXY  = 'BCC_HTTP_PROXY'
BCC_HTTPS_PROXY = 'BCC_HTTPS_PROXY'
NO_PROXY='NO_PROXY'
debug=False

def proxy_on(http=True,https=True):
    if http and (BCC_HTTP_PROXY in os.environ):
        os.environ[HTTP_PROXY]  = os.environ[BCC_HTTP_PROXY]
    if https and (BCC_HTTPS_PROXY in os.environ):
        os.environ[HTTPS_PROXY] = os.environ[BCC_HTTPS_PROXY]

def proxy_off():
    if HTTP_PROXY in os.environ:
        del os.environ[HTTP_PROXY]
    if HTTPS_PROXY in os.environ:
        del os.environ[HTTPS_PROXY]

class Proxy:    
    """Context manager that enables the Census proxy. By default http is not proxied and https is proxied.
    This allows AWS IAM Roles to operate (since they seem to be enabled by http) but we can reach the
    endpoint through the HTTPS proxy (since it's IP address is otherwise blocked). 

    This took a long time to figure out.

    Additionally, the IAM role of the server or cluster this code is running on must be able to access the
    proxy. Otherwise, it will give a botocore.exceptions.NoCredentialsError: Unable to locate credentials exception.

    Example -
    .. highlight: python
    import boto3
    from ctools.aws import Proxy

    url = "[INSERT VALID AWS URL HERE]"

    if __name__ == "__main__":

        with Proxy() as p:
            client = boto3.client('sqs')
            response = client.receive_message(
                QueueUrl=url,
                AttributeNames=[
                    'All',
                ],
                MaxNumberOfMessages=10,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=1,
                WaitTimeSeconds=1
            )
    """
    def __init__(self,http=False,https=True):
        self.http = http
        self.https = https

    def __enter__(self):
        proxy_on(http=self.http, https=self.https)
        return self

    def __exit__(self, *args):
        proxy_off()


def get_url(url, context=None, ignore_cert=False, timeout=None):
    if ignore_cert:
        import ssl
        context = ssl._create_unverified_context()

    import urllib.request
    with urllib.request.urlopen(url, context=context, timeout=timeout) as response:
        return response.read().decode('utf-8')

def get_url_json(url, **kwargs):
    return json.loads(get_url(url, **kwargs))

def user_data():
    return get_url_json("http://169.254.169.254/2016-09-02/user-data/")

def instance_identity():
    return get_url_json('http://169.254.169.254/latest/dynamic/instance-identity/document')

def ami_id():
    return get_url('http://169.254.169.254/latest/meta-data/ami-id')


def show_credentials():
    """This is mostly for debugging"""
    subprocess.call(['printenv'])
    subprocess.call(['aws','configure','list'])

def get_ipaddr():
    return get_url("http://169.254.169.254/latest/meta-data/local-ipv4")

def instanceId():
    return instance_identity()['instanceId']

if __name__=="__main__":
    print("AWS Info:")
    doc = instance_identity()
    for (k,v) in doc.items():
        print("{}: {}".format(k,v))
    print("AMI ID: {}".format(ami_id()))
