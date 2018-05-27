import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from pprint import pprint
import subprocess
from util import *

class GCPController(object):
    def __init__(self, project):
        self.compute = googleapiclient.discovery.build('compute', 'v1')
        self.project = project # constant for all operations

    def delete_all(self, compute_resource, compute_resource_name, region):
        resp = compute_resource.list(project=self.project, region=region).execute()
        for item in resp["items"]:
            print "deleting", compute_resource_name, item["name"]
            args = {compute_resource_name: item["name"], "project": self.project, "region": region}
            compute_resource.delete(**args).execute()


    def create_pool(self, src_region, dst_region):
        body = {"name": "from-%s-to-%s-pool" % (src_region, dst_region)}
        operation = self.compute.targetPools().insert(project=self.project,
                                                      region=src_region,
                                                      body=body).execute()
        self.wait_for_region_operation(src_region, operation["name"])

    def reserve_vpc_ip(self, region, instance_name):
        body = {
                    "name": "ip-" + instance_name,
                    "addressType": "INTERNAL"
                }
        operation = self.compute.addresses().insert(project=self.project, region=region, body=body).execute()
        # TODO cb/ promises
        self.wait_for_region_operation(region, operation['name'])
        resp = self.compute.addresses().get(project=self.project, region=region, address=body["name"]).execute()
        return resp["address"]

    def create_instance(self, zone, name, imageID, vcpus, script, script_params):
        # https://www.googleapis.com/compute/v1/projects/{project}/global/images/{resourceId}
        image_response = self.compute.images().get(project=self.project, image=imageID).execute()
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

        return self.compute.instances().insert(
            project=self.project,
            zone=zone,
            body=config).execute()


    def delete_instance(self, zone, name):
        return self.compute.instances().delete(
            project=self.project,
            zone=zone,
            instance=name).execute()


    def wait_for_zone_operation(self, zone, operation):
        print('Waiting for operation to finish...')
        while True:
            result = self.compute.zoneOperations().get(
                project=self.project,
                zone=zone,
                operation=operation).execute()

            if result['status'] == 'DONE':
                print("done.")
                if 'error' in result:
                    raise Exception(result['error'])
                return result

            time.sleep(1)

    def wait_for_region_operation(self, region, operation):
        print('Waiting for operation to finish...')
        while True:
            result = self.compute.regionOperations().get(
                project=self.project,
                region=region,
                operation=operation).execute()

            if result['status'] == 'DONE':
                print("done.")
                if 'error' in result:
                    raise Exception(result['error'])
                return result

            time.sleep(1)

    def keygen(self):
        call("wg genkey | tee privatekey | wg pubkey > publickey", shell=True)
        with open("privatekey", "r") as f:
            private_key = f.read()
        with open("publickey", "r") as f:
            public_key = f.read()
        return public_key[:-1], private_key[:-1]


    def expand_link(self, link):
        prefix = "rt" + str(int(time.time()))

        ipA = self.reserve_vpc_ip(link.project, link.regionA, prefix + "a")
        ipB = self.reserve_vpc_ip(link.project, link.regionB, prefix + "b")
        pprint(ipA)
        pprint(ipB)

        print('Creating instances.')

        imageID = "just-wireguard"
        vcpus = 1
        script =  "startup-script.py"

        internalApublic, internalAprivate = self.keygen()
        internalBpublic, internalBprivate = self.keygen()
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
        operationA = self.create_instance(link.project, link.zoneA, prefix + "a", imageID, vcpus, script, script_paramsA)
        operationB = self.create_instance(link.project, link.zoneB, prefix + "b", imageID, vcpus, script, script_paramsB)
        self.wait_for_zone_operation(link.project, link.zoneA, operationA['name'])
        self.wait_for_zone_operation(link.project, link.zoneB, operationB['name'])


# if __name__ == '__main__':
#     # create link
#     link = Link("proj-204902",
#                 "us-west1",
#                 "europe-west2", 
#                 "from-oregon-to-london",
#                 "from-london-to-oregon",
#                 "us-west1-b",
#                 "europe-west2-a",
#                 Client("192.168.1.0/24", "PEyAxX9TkfUZL6WtT5Wom/vUBLU58Q+Bm96HOoS8GC8="),
#                 Client("192.168.2.0/24", "V7Xk17ue208HvTP+HATwbTqCTwl5am10z1TQeIRKmB8="),
#                 "uAQZLoJJFJfEP7HmHdwhOmIrNaQ5HFtN4bxwOaFw4Gk=",
#                 # pubkey sSZRAEzYMKv8KVdnXdiKWqRWvK4GvgTog8XgS+yWDBI=
#                 "eOnUcSdci+B2lTEN+XhATLlU+Jm9TTurePnmXJtKy1k="
#                 # pubkey vkTIgND+JmGeywcVLowaj4Q2f7CSgr0qhHu6rNbzAw8=
#             )

#     expand_link(link)

