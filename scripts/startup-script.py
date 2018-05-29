#! /usr/bin/python

import requests
from subprocess import call as real_call
import sys
import json

def call(*args, **kwargs):
    print args
    real_call(*args, **kwargs)

def start_wg_interface(my_ip, if_name):
    call("sudo ip link add dev %s type wireguard" % if_name, shell=True)
    call("sudo ip address add dev %s %s/32" % (if_name, my_ip), shell=True)
    call("sudo wg setconf %s %s" % (if_name, if_name + ".conf"), shell=True)
    call("ip link set up dev %s" % if_name, shell=True)

if_idx = 0
def alloc_if_name():
    global if_idx
    if_name = "wg%d" % if_idx
    if_idx += 1
    return if_name


def main():
    # send output to file
    sys.stdout = open("startup-script.out", "w+")
    sys.stderr = open("startup-script.out", "w+")

    serialized = requests.get("http://metadata/computeMetadata/v1/instance/attributes/me",
                                            headers={"Metadata-Flavor": "Google"}).text
    me = pickle.loads(serialized)

    # allow ip forwarding
    call("sudo sysctl -w net.ipv4.ip_forward=1", shell=True)

    for endpoint, client in me.client_facing_endpoints:
        if_name = alloc_if_name()
        with open(if_name + ".conf", "w+") as f:
            f.write(endpoint.create_wireguard_config())
        start_wg_interface(me.private_ip_a, if_name)
        call("sudo ip route add %s dev %s" % (client.private_ip, if_name), shell=True) 
    
    transit_if_name = alloc_if_name()
    with open(transit_if_name + ".conf", "w+") as f:
        f.write(transit_facing_endpoint.create_wireguard_config())
    start_wg_interface(me.private_ip_b, transit_if_name)
    for endpoint, client in me.pair.client_facing_endpoints:
        call("sudo ip route add %s dev %s" % (client.private_ip, transit_if_name), shell=True) 

    sys.stdout.close()
    sys.stderr.close()

if __name__ == '__main__':
    main()
