import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from link import Link, Client
from pprint import pprint
import subprocess

def reserve_vpc_ip(compute, project, region, instance_name):
    body = {
                "name": "ip-" + instance_name,
                "addressType": "INTERNAL"
            }
    operation = compute.addresses().insert(project=project, region=region, body=body).execute()
    # TODO cb/ promises
    wait_for_region_operation(compute, project, region, operation['name'])
    resp = compute.addresses().get(project=project, region=region, address=body["name"]).execute()
    return resp["address"]

def create_instance(compute, project, zone, name, imageID, vcpus, script, script_params):
    # https://www.googleapis.com/compute/v1/projects/{project}/global/images/{resourceId}
    image_response = compute.images().get(project=project, image=imageID).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/n1-standard-%d" % (zone, vcpus)
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), script), 'r').read()

    script_params["startup-script"] = startup_script
    metadata = [{"key": k, "value": v} for k, v in script_params.iteritems()]

    config = {
        'name': name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': metadata
        },

        # allow packet routing
        'canIpForward': True
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()


def delete_instance(compute, project, zone, name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()


def wait_for_zone_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)

def wait_for_region_operation(compute, project, region, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.regionOperations().get(
            project=project,
            region=region,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)

def keygen():
    call("wg genkey | tee privatekey | wg pubkey > publickey", shell=True)
    with open("privatekey", "r") as f:
        private_key = f.read()
    with open("publickey", "r") as f:
        public_key = f.read()
    return public_key[:-1], private_key[:-1]


def expand_link(link):
    compute = googleapiclient.discovery.build('compute', 'v1')
    prefix = "hi" + str(int(time.time()))

    ipA = reserve_vpc_ip(compute, link.project, link.regionA, prefix + "a")
    ipB = reserve_vpc_ip(compute, link.project, link.regionB, prefix + "b")
    pprint(ipA)
    pprint(ipB)

    print('Creating instances.')

    imageID = "just-wireguard"
    vcpus = 1
    script =  "startup-script.py"

    internalApublic, internalAprivate = keygen()
    internalBpublic, internalBprivate = keygen()
    script_paramsA = {
                "my_internal_wg_ip": "192.168.0.2",
                "their_internal_wg_ip":"192.168.0.3",
                "their_external_wg_ip":"192.168.0.4",
                "my_external_wg_ip":"192.168.0.5",
                "our_cidr": link.clientA.cidr,
                "their_cidr": link.clientB.cidr,
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "our_external_port":"3002",
                "my_internal_private_key": internalAprivate,
                "their_internal_public_key": internalBpublic,
                "our_external_private_key": link.external_private_keyA,
                "our_clients_public_key": link.clientA.public_key,
                "their_vpc_address": ipB
            }
    script_paramsB = {
                "my_internal_wg_ip":"192.168.0.3",
                "their_internal_wg_ip": "192.168.0.2",
                "their_external_wg_ip":"192.168.0.5",
                "my_external_wg_ip":"192.168.0.4",
                "our_cidr": link.clientB.cidr,
                "their_cidr": link.clientA.cidr,
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "our_external_port":"3002",
                "my_internal_private_key": internalBprivate,
                "their_internal_public_key": internalApublic,
                "our_external_private_key": link.external_private_keyB,
                "our_clients_public_key": link.clientB.public_key,
                "their_vpc_address": ipA
            }
    operationA = create_instance(compute, link.project, link.zoneA, prefix + "a", imageID, vcpus, script, script_paramsA)
    operationB = create_instance(compute, link.project, link.zoneB, prefix + "b", imageID, vcpus, script, script_paramsB)
    wait_for_zone_operation(compute, link.project, link.zoneA, operationA['name'])
    wait_for_zone_operation(compute, link.project, link.zoneB, operationB['name'])


if __name__ == '__main__':
    # create link
    link = Link("proj-204902",
                "us-west1",
                "europe-west2", 
                "from-oregon-to-london",
                "from-london-to-oregon",
                "us-west1-b",
                "europe-west2-a",
                Client("192.168.1.0/24", "PEyAxX9TkfUZL6WtT5Wom/vUBLU58Q+Bm96HOoS8GC8="),
                Client("192.168.2.0/24", "V7Xk17ue208HvTP+HATwbTqCTwl5am10z1TQeIRKmB8="),
                "uAQZLoJJFJfEP7HmHdwhOmIrNaQ5HFtN4bxwOaFw4Gk=",
                # pubkey sSZRAEzYMKv8KVdnXdiKWqRWvK4GvgTog8XgS+yWDBI=
                "eOnUcSdci+B2lTEN+XhATLlU+Jm9TTurePnmXJtKy1k="
                # pubkey vkTIgND+JmGeywcVLowaj4Q2f7CSgr0qhHu6rNbzAw8=
            )

    expand_link(link)

