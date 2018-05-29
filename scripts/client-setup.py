#! /usr/bin/python

import argparse
import requests
import sys
import json
from pprint import pprint
import os
import pickle
from link import *

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = pickle.load(f)
    nodes = config["nodes"]
    me = config["me"]
    for node_name, tuples in me.transits.iteritems():
        interfaces = []
        for endpoint, transit in tuples:
            if_name = endpoint.realize(me.private_ip)
            interfaces.append(if_name)
            transit_ips = []
            transit_ips.append(transit.private_ip_a)
            transit_ips.append(transit.private_ip_b)
            transit_ips.append(transit.pair.private_ip_a)
            transit_ips.append(transit.pair.private_ip_b)
            for transit_ip in transit_ips:
                call("sudo ip route add %s dev %s" % (transit_ip, if_name), shell=True) 
        nh_string = ""
        for interface in interfaces:
            nh_string += "nexthop dev %s weight 1 " % interface
        dst_node = next(n for n in nodes if n.name == node_name)
        for client in dst_node.clients:
            call("sudo ip route add %s %s" % (client.private_ip, nh_string), shell=True)

if __name__ == '__main__':
    if os.getuid() != 0:
        print "must run as root user"
        exit(1)
    main()
