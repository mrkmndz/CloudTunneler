import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from pprint import pprint
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

v_i = 0
def allocate_virtual_ip():
    global v_i
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
        from_transits = [Transit(gcp.reserve_vpc_ip(from_node.region, is_internal=False),
                                    gcp.reserve_vpc_ip(from_node.region),
                                    allocate_virtual_ip(),
                                    allocate_virtual_ip(),
                                    edge["internal_tunnel"]) for x in range(width)]
        from_node.transits += from_transits

        to_transits = [Transit(gcp.reserve_vpc_ip(to_node.region, is_internal=False),
                                    gcp.reserve_vpc_ip(to_node.region),
                                    allocate_virtual_ip(),
                                    allocate_virtual_ip(),
                                    edge["internal_tunnel"]) for x in range(width)]
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
    for node in nodes:
        print "setting up node %s" % node.name
        operations = []
        for i, transit in enumerate(node.transits):
            instance_name = "%s-%d-transit" % (node.name, i)
            if not transit.internal_tunnel:
                for endpoint, client in transit.pair.client_facing_endpoints:
                    sanitized_ip = client.private_ip.replace(".","-")
                    name = "%s-to-%s" % (instance_name, sanitized_ip)
                    cidr = "%s/32" % client.private_ip
                    nhip = transit.pair.vpc_ip
                    gcp.add_route(name, [instance_name], 2003, cidr, nhip)
            serialized = pickle.dumps(transit)
            operations.append(gcp.create_instance(node.zone,
                                                    instance_name,
                                                    transit.vpc_ip,
                                                    transit.client_facing_ip,
                                                    "preppedv3",
                                                    4,
                                                    "startup-script.bash",
                                                    {"me": serialized}))
        for operation in operations:
            gcp.wait_for_zone_operation(node.zone, operation["name"])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
