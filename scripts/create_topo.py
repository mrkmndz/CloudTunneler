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
    with open(config_file, "r") as f:
        config = json.load(f)
    build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    if os.path.isdir(build_dir):
        print "topology already exists"
        return

    gcp = GCPController(config["project"])

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
                        link = next(x for x in links if x.is(region, other_region))
                        my_rgs.append(link.router_group_a)
                    except StopIteration as e:
                        link = next(x for x in links if x.is(other_region, region))
                        my_rgs.append(link.router_group_b)
            obj["links"] = [{"public_key": x.client_facing_public_key,
                                "ip_addr": x.pool.ip
                                "port": 3002
                                "allowed_ips": [other_region["cidr"]]}
                                for x in my_rgs]

            with open(os.path.join(build_dir), region + "-client-%d" % client_idx, "w+") as f:
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
