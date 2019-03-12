#!/usr/bin/env python3
#
# cluster_info.py:
# A module of useful EMR cluster management tools.
# We've had to build our own to work within the Census Environment
# This script appears in:
#   das-vm-config/bin/cluster_info.py
#   emr_stats/cluster_info.py
#
# Currently we manually sync the two; perhaps it should be moved to ctools.

import os
import sys
from pathlib import Path
import json

import subprocess
from subprocess import Popen,PIPE,call

HTTP_PROXY='HTTP_PROXY'
HTTPS_PROXY='HTTPS_PROXY'
BCC_PROXY='BCC_PROXY'

_isMaster ='isMaster'
_isSlave  = 'isSlave'
_clusterId = 'clusterId'
_diskEncryptionConfiguration='diskEncryptionConfiguration'
_encryptionEnabled='encryptionEnabled'

def proxy_on():
    os.environ[HTTP_PROXY]  = os.environ[BCC_PROXY]
    os.environ[HTTPS_PROXY] = os.environ[BCC_PROXY]

def proxy_off():
    del os.environ[HTTP_PROXY]
    del os.environ[HTTPS_PROXY]


def user_data():
    """Return the userdata associated with this instance"""
    return json.loads(subprocess.run(['curl','-s','http://169.254.169.254/2016-09-02/user-data/'],stdout=subprocess.PIPE).stdout)

def isMaster():
    """Returns true if running on master"""
    return user_data()['isMaster']

def isSlave():
    """Returns true if running on master"""
    return user_data()['isSlave']

def phost(host):
    return host if host else "Head node"

def decode_status(meminfo):
    return { line[:line.find(":")] : line[line.find(":")+1:].strip() for line in meminfo.split("\n") }

def clusterID():
    return os.environ['CLUSTERID']

def run_command_on_host(host,command,encoding='utf-8',pipeerror=None):
    error_out = PIPE if pipeerror else sys.stdout
    if host=="":
        data=Popen(command,shell=True,stdout=PIPE,stderr=error_out).communicate()[0]
    else:
        data=Popen(["ssh",host,command],stdout=PIPE,stderr=error_out).communicate()[0]
    if encoding:
        return data.decode(encoding)
    else:
        return data

def get_file_on_host(host,path,encoding='utf-8'):
    return run_command_on_host(host,"/bin/cat "+path,encoding=encoding)

def get_instance_type(host):
    return run_command_on_host(host,"curl -s http://169.254.169.254/latest/meta-data/instance-type")

def get_url(url):
    import urllib.request
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')

def get_ipaddr():
    return get_url("http://169.254.169.254/latest/meta-data/local-ipv4")

def decode_kb(msg):
    try:
        (numbers,units) = msg.split(" ")
    except ValueError:
        return msg
    numbers = int(numbers)
    if units=='kB':
        numbers //= (1024*1024)
        units = 'GiB'
    return "{} {}".format(numbers,units)

def print_stats_for_host(host):
    meminfo = decode_status(get_file_on_host(host,"/proc/meminfo"))
    status  = decode_status(get_file_on_host(host,"/proc/self/status"))
    cpuinfo = get_file_on_host(host,"/proc/cpuinfo")
    cpus = 0
    total_cores = 0
    for line in cpuinfo.split("\n"):
        if line.startswith("processor"): cpus += 1
        if line.startswith("cpu cores"): total_cores += int(line[line.find(":")+2:])
    itype = get_instance_type(host)

    print("{:34} {:14} Memory: {:8}".format(phost(host),itype,decode_kb(meminfo.get('MemTotal',''))))

def cluster_hostnames(getMaster=True):
    if isMaster and getMaster:
        yield get_ipaddr()
    for line in run_command_on_host('','yarn node -list',pipeerror=True).split('\n'):
        if "RUNNING" in line:
            host = line[0:line.find(':')]
            yield(host)

if __name__=="__main__":
    from argparse import ArgumentParser,ArgumentDefaultsHelpFormatter
    parser = ArgumentParser( formatter_class = ArgumentDefaultsHelpFormatter,
                             description="Tools for working with the Census Cluster." )
    parser.add_argument("--list",help="List nodes in the cluster.",action='store_true')
    parser.add_argument("--dist",help="Distribute your SSH public key from this machine to the others",action='store_true')
    parser.add_argument("--check",help="try to log into each host",action='store_true')
    args = parser.parse_args()

    data = user_data()

    if data[_isMaster]:
        print("Running on Master")
    if data[_isSlave]:
        print("Running on Slave")
    print("clusterid:",data[_clusterId])
    print("diskEncryptionConfiguration.encryptionEnabled:",data[_diskEncryptionConfiguration][_encryptionEnabled])

    if args.list:
        for host in cluster_hostnames():
            print(host)
        exit(0)
    
    if args.dist:
        privkey_fname = os.path.join(Path.home(),".ssh/id_rsa")
        pubkey_fname = os.path.join(Path.home(),".ssh/id_rsa.pub")

        if not os.path.exists(pubkey_fname):
            print("Creating a SSH public/private key pair for this system")
            try:
                subprocess.run(['ssh-keygen','-P','','-f',privkey_fname,'-t','rsa'],check=True)
            except subprocess.CalledProcessError as e:
                print("Cannot make public key pair")
                raise e
        print("Distributing your public key to each machine. You will have to type your password several times.")
        for host in cluster_hostnames():
            print("{}:".format(host))
            cmd = ['ssh',host,'-o','StrictHostKeyChecking=no',
                   'test -f {} || ssh-keygen -P "" -f {} -t rsa; umask 0077; cat >> .ssh/authorized_keys'.format(
                privkey_fname,privkey_fname)]
            print(" ".join(cmd))
            subprocess.run(cmd,stdin=open(pubkey_fname),check=True)
        exit(0)

    if args.check:
        for host in cluster_hostnames():
            print(run_command_on_host(host,command='hostname; uptime'))
        exit(0)

    # Distribute SSH key to other machines
    #for host in cluster_hostnames():
    #    call(["ssh",host,"mkdir -p .ssh; chmod 700 .ssh ; cat >> .ssh/authorized_keys"],
    #          stdin=open(os.path.join(os.environ["HOME"],".ssh/id_rsa.pub")))
              
    hosts = list(cluster_hostnames(getMaster=False))
        
    print("====================")
    print("== CPU AND MEMORY ==")
    print("====================")

    for host in [''] + hosts:
        print_stats_for_host(host)

    print("==================")
    print("== FILE SYSTEMS ==")
    print("==================")

    for host in [''] + hosts:
        print(phost(host ))
        print(run_command_on_host(host,"df -h"))
        #print(run_command_on_host(host,"/sbin/blkid /dev/xvdb2"))

    print("== HDFS STATUS ==")
    print(run_command_on_host('',"hdfs dfs -df -h"))
