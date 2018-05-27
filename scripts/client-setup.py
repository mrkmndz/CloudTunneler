#! /usr/bin/python

import requests
from subprocess import call as real_call
import sys
import json

def call(*args, **kwargs):
    print args
    real_call(*args, **kwargs)


def start_wg_interface(my_ip, wan_cidr, config):
    call("sudo ip link add dev wg0 type wireguard", shell=True)
    call("sudo ip address add dev wg0 %s/32" % my_ip, shell=True)
    call("sudo wg setconf wg0 %s" % config, shell=True)
    call("ip link set up dev wg0", shell=True)
    call("sudo ip route add %s dev wg0" % wan_cidr, shell=True)

def create_wireguard_config(wan_config):
    conf_str = ("[Interface]\n"
                "PrivateKey = {my_private_key}\n"
                "ListenPort = {my_port}\n").format(**wan_config)
    for link in wan_config["links"]:
        conf_str += ("[Peer]\n"
            "PublicKey = {public_key}\n"
            "Endpoint = {ip_addr}:{port}\n"
            "AllowedIPs = {allowed_ips}\n").format(**link, allowed_ips=link.cidrs.join(", "))
    return conf_str

def main():
    with open("config.json", "r") as f:
        config = json.load(f)
    with open(wg_config, "w+") as f:
        f.write(create_wireguard_config(config)
    start_wg_interface(config["my_ip"], config["wan_cidr"], wg_config)

if __name__ == '__main__':
    main()
