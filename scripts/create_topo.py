import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from pprint import pprint
from subprocess import call
import json
from gcp_controller import GCPController
from pprint import pprint
from link import *
import pickle
PROJECT = "cloudtunneler"

def create_link(project, regionA, regionB, clients):
    rg_a = RouterGroup(regionA["name"],
                       regionA["zone"],
                       clients[regionA["name"]])
    rg_b = RouterGroup(regionB["name"],
                       regionB["zone"],
                       clients[regionB["name"]])
    link = Link(project,
                rg_a,
                rg_b)
    return link

pip_i = 0
def allocate_public_ip():
    pip_i += 1
    return "10.%d.10.10" % pip_i

vpc_i = 0
def allocate_vpc_ip():
    vpc_i += 1
    return "10.%d.10.11" % vpc_i

v_i = 0
def allocate_virtual_ip():
    v_i += 1
    return "10.%d.10.12" % v_i

def main(config_file):
    with open(config_file, "r") as f:
        config = json.load(f)

    topo_name = config["name"]

    build_dir = os.path.join(os.path.dirname(__file__), topo_name + "-build")
    if os.path.isdir(build_dir):
        print "topology already exists"
        return

    gcp_project = config["project"] 

    nodes = [Node(x) for x in config["nodes"]]

    gcp = GCPController(gcp_project)

    for edge in config["edges"]:
        from_node = next(n for n in nodes if n.name == edge["from"])
        to_node = next(n for n in nodes if n.name == edge["to"])
        width = edge["width"]
        from_transits = [Transit(allocate_public_ip(),
                                    allocate_vpc_ip(),
                                    allocate_virtual_ip(),
                                    allocate_virtual_ip()) for x in range(width)]
        from_node.transits += from_transits

        to_transits = [Transit(allocate_public_ip(),
                                    allocate_vpc_ip(),
                                    allocate_virtual_ip(),
                                    allocate_virtual_ip()) for x in range(width)]
        to_node.transits += to_transits

        for x in range(width):
            from_transits[x].pair_with(to_transits[x])

        for client in from_node.clients:
            client.gain_transits_to_node(to_node, from_transits)

        for client in to_node.clients:
            client.gain_transits_to_node(from_node, to_transits)

    # create client configs
    call("mkdir " + build_dir, shell=True)
    for node in nodes:
        for i, client in enumerate(node.clients):
            file_name = "%s-client-%d.pickle" % (node.name, i)
            with open(os.path.join(build_dir, file_name), "w+") as f:
                pickle.dump({"nodes": nodes, "me": client}, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
