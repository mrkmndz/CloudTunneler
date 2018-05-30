import argparse
import json
from gcp_controller import GCPController
from subprocess import call
import os
from link import *

def main(config_file):
    with open(config_file, "r") as f:
        config = json.load(f)
    gcp = GCPController(config["project"])
    nodes = [Node(x) for x in config["nodes"]]
    # tuples of region or zone and operation
    region_operations = []
    zone_operations = []
    for node in nodes:
        # delete ip address
        region_ops = gcp.delete_all(gcp.compute.addresses(), "address", node.region)
        region_operations.append((node.region, region_ops))
        # delete instances
        zone_ops = gcp.delete_all_instances(node.zone)
        zone_operations.append((node.zone, zone_ops))
    for region, ops in region_operations:
        for operation in ops:
            gcp.wait_for_region_operation(region, operation["name"])
    for zone, ops in zone_operations:
        for operation in ops:
            gcp.wait_for_zone_operation(zone, operation["name"])
    build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    call("rm -rf " + build_dir, shell=True)   

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
