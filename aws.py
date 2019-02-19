import json
import requests



def instance_identity():
    r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
    return json.loads(r.text)


def ami_id():
    r = requests.get('curl http://169.254.169.254/latest/meta-data/ami-id')
    return r.test


if __name__=="__main__":
    print("AWS Info:")
    doc = instance_identity()
    for (k,v) in doc.items():
        print("{}: {}".format(k,v))
    print("AMI ID: {}".format(ami_id()))
