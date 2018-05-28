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
from link import Client, Link
PROJECT = "cloudtunneler"

def create_client():
    return Client("test", "test")

def create_link(project, regionA, regionB, pools, clients):
    link = Link(project,
                regionA["name"],
                regionB["name"],
                pools[regionA["name"]],
                pools[regionB["name"]],
                regionA["zone"],
                regionB["zone"],
                clients[regionA["name"]],
                clients[regionB["name"]],
                "tmp",
                "tmp")
    return link

def init_pool(gcp, src_region, dst_region):
    # create pool
    pool_name = gcp.create_pool(src_region, dst_region)
    # create forwarding rule
    gcp.forward_to_pool(pool_name, src_region)

    return pool_name

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
        # TODO only doing 1 client per region
        clients[region["name"]] = create_client()

    num_regions = len(config["regions"])
    for i in range(num_regions):
        regionA = config["regions"][i]
        for j in range(i+1, num_regions):
            regionB = config["regions"][j]
            pools[regionA["name"]], pools[regionB["name"]] = init_pools(gcp,
                                                                        regionA["name"],
                                                                        regionB["name"])
            link = create_link(gcp.project, regionA, regionB, pools, clients)
            pprint(link.__dict__)
            # expand_link(link)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
