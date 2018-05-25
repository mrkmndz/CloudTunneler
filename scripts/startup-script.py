#! /usr/bin/python

import requests
from subprocess import call as real_call
import sys

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
    return ("[Interface]\n"
            "PrivateKey = {my_internal_private_key}\n"
            "ListenPort = {my_internal_port}\n"
            "[Peer]\n"
            "PublicKey = {their_internal_public_key}\n"
            "Endpoint = {their_vpc_address}:{their_internal_port}\n"
            "AllowedIPs = {their_internal_wg_ip}, {their_cidr}").format(**settings)

def create_external_wireguard_config(settings):
    return ("[Interface]\n"
            "PrivateKey = {our_external_private_key}\n"
            "ListenPort = {our_external_port}\n"
            "[Peer]\n"
            "PublicKey = {our_clients_public_key}\n"
            "AllowedIPs = {our_cidr}").format(**settings)

def main():
    # send output to file
    # sys.stdout = open("startup-script.out", "w+")
    # sys.stderr = open("startup-script.out", "w+")

    # get settings
    all_settings = ["my_internal_wg_ip",
                    "their_cidr",
                    "their_internal_wg_ip",
                    "their_external_wg_ip",
                    "my_external_wg_ip",
                    "our_cidr",
                    "my_internal_private_key",
                    "my_internal_port",
                    "their_internal_public_key",
                    "their_vpc_address",
                    "their_internal_port",
                    "our_external_private_key",
                    "our_external_port",
                    "our_clients_public_key"]
    settings = {
                "my_internal_wg_ip": "192.168.0.2",
                "their_cidr":"192.168.1.0/24",
                "their_internal_wg_ip":"192.168.0.3",
                "their_external_wg_ip":"192.168.0.4",
                "my_external_wg_ip":"192.168.0.5",
                "our_cidr":"192.168.2.0/24",
                "my_internal_private_key":"GHSS1c/i6IWEZ5KDiGfivsO9keNoHN5KS7M+Wrjmq18=",#TODO
                "my_internal_port":"3005",
                "their_internal_public_key":"mSIHl0o0U6n9QDEptYCypaL4DCWC3ipN1nmIYZaa3A0=",#TODO
                "their_vpc_address":"10.138.0.2",#TODO
                "their_internal_port":"3005",
                "our_external_private_key": "GHSS1c/i6IWEZ5KDiGfivsO9keNoHN5KS7M+Wrjmq18=",#TODO
                "our_external_port":"3002",
                "our_clients_public_key":"V7Xk17ue208HvTP+HATwbTqCTwl5am10z1TQeIRKmB8="#TODO
            }
    def swap(pa, pb):
        settings[pa], settings[pb] = settings[pb], settings[pa]
    swap("my_internal_wg_ip", "their_internal_wg_ip")
    swap("my_external_wg_ip", "their_external_wg_ip")
    swap("their_cidr", "our_cidr")
    settings["my_internal_private_key"] = "kOQXfqm+YFBSR7erwNLNezahoLGrHJwbiYgbxnV5/Ww="
    settings["our_external_private_key"] = "kOQXfqm+YFBSR7erwNLNezahoLGrHJwbiYgbxnV5/Ww="
    settings["their_internal_public_key"] = "5QXBOMtztySA4E1y2DgwI500+uXpcOhljPyEfWtdlzE="
    settings["our_clients_public_key"] = "PEyAxX9TkfUZL6WtT5Wom/vUBLU58Q+Bm96HOoS8GC8="
    settings["their_vpc_address"] = "10.154.0.2"
    # for setting in all_settings:
    #     settings[setting] = requests.get("http://metadata/computeMetadata/v1/instance/attributes/%s" % setting,
    #                                         headers={"Metadata-Flavor: Google"})

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
