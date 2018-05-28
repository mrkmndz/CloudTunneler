#! /usr/bin/python

import requests
from subprocess import call as real_call
import sys
import json

def call(*args, **kwargs):
    print args
    real_call(*args, **kwargs)


def start_wg_interface(is_internal, config, settings):
    iface_name = "wg%d" % (1 if is_internal else 0)
    call("sudo ip link add dev %s type wireguard" % iface_name, shell=True)
    if is_internal:
        call("sudo ip address add dev {iname} {my_internal_wg_ip}/32".format(iname=iface_name, **settings), shell=True)
    else:
        call("sudo ip address add dev {iname} {my_external_wg_ip}/32".format(iname=iface_name, **settings), shell=True)
    call("sudo wg setconf %s %s" % (iface_name, config), shell=True)
    call("ip link set up dev %s" % iface_name, shell=True)
    if is_internal:
        call("sudo ip route add {their_cidr} dev {iname}".format(iname=iface_name, **settings), shell=True)
        call("sudo ip route add {their_internal_wg_ip} dev {iname}".format(iname=iface_name, **settings), shell=True)
        call("sudo ip route add {their_external_wg_ip} dev {iname}".format(iname=iface_name, **settings), shell=True)
    else:
        call("sudo ip route add {our_cidr} dev {iname}".format(iname=iface_name, **settings), shell=True)

def create_internal_wireguard_config(settings):
    their_clients_ips_str = ", ".join([c["ip"] for c in settings["their_clients"]])
    return ("[Interface]\n"
            "PrivateKey = {my_internal_private_key}\n"
            "ListenPort = {my_internal_port}\n"
            "[Peer]\n"
            "PublicKey = {their_internal_public_key}\n"
            "Endpoint = {their_vpc_address}:{their_internal_port}\n"
            "AllowedIPs = {their_external_wg_ip}, {their_internal_wg_ip}, {their_clients_ips}").format(**settings, 
                                                        their_clients_ips=their_client_ips_str)

def create_external_wireguard_config(settings):
    config = ("[Interface]\n"
            "PrivateKey = {our_external_private_key}\n"
            "ListenPort = {our_external_port}\n").format(**settings)

    for client in settings["our_clients"]:
        config += ("[Peer]\n"
                   "PublicKey = {public_key}\n"
                   "AllowedIPs = {ip}\n").format(**client)

def main():
    # send output to file
    sys.stdout = open("startup-script.out", "w+")
    sys.stderr = open("startup-script.out", "w+")

    # get settings
    all_settings = ["my_internal_wg_ip",
                    "their_internal_wg_ip",
                    "their_external_wg_ip",
                    "my_external_wg_ip",
                    "my_internal_port",
                    "their_internal_port",
                    "our_external_port",
                    "my_internal_private_key",
                    "their_internal_public_key",
                    "our_external_private_key",
                    "their_vpc_address",
                    "our_clients",
                    "their_clients"]
    settings = {}
    for setting in all_settings:
        settings[setting] = requests.get("http://metadata/computeMetadata/v1/instance/attributes/%s" % setting,
                                            headers={"Metadata-Flavor": "Google"}).text

    settings["our_clients"] = json.loads(settings["our_clients"])
    settings["their_clients"] = json.loads(settings["their_clients"])

    # allow ip forwarding
    call("sudo sysctl -w net.ipv4.ip_forward=1", shell=True)

    # create internal link
    external_config = "external.config"
    with open(external_config, "w+") as f:
        f.write(create_external_wireguard_config(settings))
    start_wg_interface(False, external_config, settings)
    internal_config = "internal.config"
    with open(internal_config, "w+") as f:
        f.write(create_internal_wireguard_config(settings))
    start_wg_interface(True, internal_config, settings)

    sys.stdout.close()
    sys.stderr.close()

if __name__ == '__main__':
    main()
