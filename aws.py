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
BCC_PROXY='BCC_PROXY'

class Proxy:    
    def __init__(self):
        pass

    def __enter__(self):
        if BCC_PROXY in os.environ:
            os.environ[HTTP_PROXY] = os.environ[BCC_PROXY]
            os.environ[HTTPS_PROXY] = os.environ[BCC_PROXY]
        return self

    def __exit__(self, *args):
        del os.environ[HTTP_PROXY]
        del os.environ[HTTPS_PROXY]



def emr_describe_cluster(clusterId):
    """Get the cluster info"""
    with Proxy() as p:
        return json.loads(subprocess.check_output(['aws','emr','describe-cluster','--output','json','--cluster-id',clusterId]))['Cluster']

def emr_list_instances(clusterId):
    """Get the list of instances for this cluster in json output"""
    with Proxy() as p:
        return json.loads(subprocess.check_output(['aws','emr','list-instances','--output','json','--cluster-id',clusterId]))['Instances']

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
