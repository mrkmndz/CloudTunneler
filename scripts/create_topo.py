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

def create_link(project, regionA, regionB, pools, clients):
    rg_a = RouterGroup(regionA["name"],
                       regionA["zone"],
                       pools[regionA["name"]],
                       clients[regionA["name"]])
    rg_b = RouterGroup(regionB["name"],
                       regionB["zone"],
                       pools[regionB["name"]],
                       clients[regionB["name"]])
    link = Link(project,
                rg_a,
                rg_b)
    return link

def init_pool(gcp, src_region, dst_region):
    # create pool
    pool_name = gcp.create_pool(src_region, dst_region)
    # reserve ip
    pool_ip = gcp.reserve_vpc_ip(src_region, pool_name, is_internal=False)
    # create forwarding rule
    gcp.forward_to_pool(pool_name, pool_ip, src_region)

    return Pool(pool_name, pool_ip)

def init_pools(gcp, src_region, dst_region):
    pool_nameA = init_pool(gcp, src_region, dst_region)
    pool_nameB = init_pool(gcp, dst_region, src_region)

    return pool_nameA, pool_nameB

def main(config_file):
    gcp = GCPController("proj-204902")
    with open(config_file, "r") as f:
        config = json.load(f)

    # TODO more efficient way to wait for operations
    clients = {} # dict of all client objects... region -> client
    pools = {} # dict of created pools... region -> pool

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
            pools[regionA["name"]], pools[regionB["name"]] = init_pools(gcp,
                                                                        regionA["name"],
                                                                        regionB["name"])
            links.append(create_link(gcp.project, regionA, regionB, pools, clients))
            # expand_link(link)
    
    # save for later
    with open("links.pickle", "w+") as f:
        pickle.dump(links, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
