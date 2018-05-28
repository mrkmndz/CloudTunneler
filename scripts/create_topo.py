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

def main(config_file):
    with open(config_file, "r") as f:
        config = json.load(f)
    build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    if os.path.isdir(build_dir):
        print "topology already exists"
        return

    gcp = GCPController(config["project"])

    # TODO more efficient way to wait for operations
    clients = {} # dict of all client objects... region -> client

    # create all clients
    for region in config["regions"]:
        for ip in region["clients"]:
            clients.setdefault(region["name"], []).append(Client(ip))

    num_regions = len(config["regions"])
    links = []
    for i in range(num_regions):
        regionA = config["regions"][i]
        for j in range(i+1, num_regions):
            regionB = config["regions"][j]
            links.append(create_link(gcp.project, regionA, regionB, clients))
            # expand_link(link)

    # create client configs
    call("mkdir " + build_dir, shell=True)
    for region, clis in clients.iteritems():
        client_idx = 0
        for client in clis:
            obj = {"my_ip": client.ip,
                    "wan_cidr": "192.168.0.0/16",
                    "my_private_key": client.private_key,
                    "my_port": 5001}
            my_rgs = []
            for other_region_obj in config["regions"]:
                other_region = other_region_obj["name"]
                if other_region != region:
                    try:
                        link = next(x for x in links if x.equals(region, other_region))
                        my_rgs.append((link.router_group_a, other_region_obj["cidr"]))
                    except StopIteration as e:
                        link = next(x for x in links if x.equals(other_region, region))
                        my_rgs.append((link.router_group_b, other_region_obj["cidr"]))
            obj["links"] = [{"public_key": x.client_facing_public_key,
                                "ip_addr": x.pool.ip,
                                "port": 3002,
                                "allowed_ips": [cidr]}
                                for x, cidr in my_rgs]

            file_name = "%s-client%d.json" % (region, client_idx)
            with open(os.path.join(build_dir, file_name), "w+") as f:
                json.dump(obj, f)
            client_idx += 1


    
    # save for later
    with open(os.path.join(build_dir, config["name"] + ".pickle"), "w+") as f:
        pickle.dump(links, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
