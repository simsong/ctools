import json
import requests
import subprocess


Ec2InstanceId='Ec2InstanceId'
Status='Status'

def create_tag(*,resourceId,key_value_pairs):
    cmd = ['aws','ec2','create-tags','--resources',resource]
    for (key,value) in key_value_pairs:
        cmd += ['--tags',f'Key={key},Value={value}']
    subprocess.check_call(cmd)

def describe_tags(*,resourceId):
    cmd = ['aws','ec2','describe-tags','--filters',f'Name=resource-id,Values={resourceId}','--output','json','--no-paginate']
    return json.loads(subprocess.check_output(cmd))['Tags']

