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
    for node in nodes:
        # delete ip address
        gcp.delete_all(gcp.compute.addresses(), "address", node.region)
        # delete instances
        gcp.delete_all_instances(node.zone)
    build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    call("rm -rf " + build_dir, shell=True)   

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
