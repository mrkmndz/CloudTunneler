import argparse
import os
import time

import googleapiclient.discovery
from six.moves import input
from pprint import pprint
from subprocess import call
import json
from util import *
from gcp_controller import GCPController
from pprint import pprint
PROJECT = "cloudtunneler"

def create_client():
    return Client(cidr="test", public_key="test")

def create_link(regionA, regionB, pools, clients):
    link = Link(project=PROJECT,
                regionA=regionA["name"],
                regionB=regionB["name"],
                poolA=pools[regionA["name"]],
                poolB=pools[regionB["name"]],
                zoneA=regionA["zone"],
                zoneB=regionB["zone"],
                clientA=clients[regionA["name"]],
                clientB=clients[regionB["name"]],
                external_private_keyA="tmp",
                external_private_keyB="tmp")
    return link

def init_pools(gcp, src_region, dst_region):
    # create pool
    pool_nameA = gcp.create_pool(src_region, dst_region)
    # create forwarding rule
    gcp.forward_to_pool(pool_nameA, src_region)
    # create pool
    pool_nameB = gcp.create_pool(dst_region, src_region)
    # create forwarding rule
    gcp.forward_to_pool(pool_nameB, dst_region)

    return pool_nameA, pool_nameB

def get_or_init_pools(gcp, src_region, dst_region, pools):
    if src_region in pools:
        assert dst_region in pools
        return pools[src_region], pools[dst_region]
    else:
        return init_pools(gcp, src_region, dst_region)

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

    for regionA in config["regions"]:
        for regionB in config["regions"]:
            if regionA["name"] != regionB["name"]:
                pools[regionA["name"]], pools[regionB["name"]] = get_or_init_pools(gcp, regionA["name"], regionB["name"])
                link = create_link(regionA, regionB, pools, clients)
                pprint(link)
                # expand_link(link)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
