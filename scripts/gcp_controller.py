import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from pprint import pprint
import subprocess
from util import *

ip_idx = 0
class GCPController(object):
    def __init__(self, project):
        self.compute = googleapiclient.discovery.build('compute', 'v1')
        self.project = project # constant for all operations

    def delete_all(self, compute_resource, compute_resource_name, region):
        resp = compute_resource.list(project=self.project, region=region).execute()
        if "items" in resp:
            for item in resp["items"]:
                print "deleting", compute_resource_name, item["name"]
                args = {compute_resource_name: item["name"], "project": self.project, "region": region}
                operation = compute_resource.delete(**args).execute()
                self.wait_for_region_operation(region, operation["name"])

    def delete_all_instances(self, zone):
        resp = self.compute.instances().list(project=self.project, zone=zone).execute()
        if "items" in resp:
            for item in resp["items"]:
                print "deleting instance", item["name"]
                args = {"instance": item["name"], "project": self.project, "zone": zone}
                operation = self.compute.instances().delete(**args).execute()
                self.wait_for_zone_operation(zone, operation["name"])

    def add_instance_to_pool(self, instance_self_link, pool_name, region):
        body = {"instances": [{"instance": instance_self_link}]}
        operation = self.compute.targetPools().addInstance(project=self.project,
                                                           region=region,
                                                           targetPool=pool_name,
                                                           body=body).execute()
        self.wait_for_region_operation(region, operation["name"])

    def create_pool(self, src_region, dst_region):
        pool_name = "from-%s-to-%s-pool" % (src_region, dst_region)
        body = {"name": pool_name, "sessionAffinity": "CLIENT_IP_PROTO"}
        operation = self.compute.targetPools().insert(project=self.project,
                                                      region=src_region,
                                                      body=body).execute()
        self.wait_for_region_operation(src_region, operation["name"])
        return pool_name

    def forward_to_pool(self, pool_name, pool_ip, region):
        pool_self_link = "projects/{project}/regions/{region}/targetPools/{pool_name}".format(
                project=self.project, region=region, pool_name=pool_name)
        body = {"target": pool_self_link,
                "name": "forward-%s" % pool_name,
                "IPProtocol": "UDP",
                "IPAddress": pool_ip}
        operation = self.compute.forwardingRules().insert(project=self.project, region=region, body=body).execute()
        self.wait_for_region_operation(region, operation["name"])

    def reserve_vpc_ip(self, region, instance_name=None, is_internal=True):
        global ip_idx
        if instance_name is None:
            instance_name = "%d-rt" % ip_idx
            ip_idx += 1
        body = {
                    "name": "ip-" + instance_name,
                    "addressType": "INTERNAL" if is_internal else "EXTERNAL"
                }
        operation = self.compute.addresses().insert(project=self.project, region=region, body=body).execute()
        # TODO cb/ promises
        self.wait_for_region_operation(region, operation['name'])
        resp = self.compute.addresses().get(project=self.project, region=region, address=body["name"]).execute()
        return resp["address"]

    def create_instance(self, zone, name, internal_ip, external_ip, imageID, vcpus, script, script_params):
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
                "networkIP": internal_ip,
                'accessConfigs': [
                    {'type': 'ONE_TO_ONE_NAT',
                        'name': 'External NAT',
                        'natIP': external_ip}
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

