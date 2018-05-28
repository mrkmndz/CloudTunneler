from keygen import keygen
from link import Link, Client
from gcp_controller import GCPController
import time
from pprint import pprint
import pickle
import argparse
import json
import os

def expand_link(controller, link):
    prefix = "rt" + str(int(time.time()))

    ipA = controller.reserve_vpc_ip(link.regionA, prefix + "a")
    ipB = controller.reserve_vpc_ip(link.regionB, prefix + "b")
    pprint(ipA)
    pprint(ipB)

    print('Creating instances.')

    #TODO maybe put this somewhere else
    imageID = "just-wireguard"
    vcpus = 4
    script =  "startup-script.py"

    internalApublic, internalAprivate = keygen()
    internalBpublic, internalBprivate = keygen()
    script_paramsA = {
                "my_internal_wg_ip": "192.168.0.2",
                "their_internal_wg_ip":"192.168.0.3",
                "their_external_wg_ip":"192.168.0.4",
                "my_external_wg_ip":"192.168.0.5",
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "our_external_port":"3002",
                "my_internal_private_key": internalAprivate,
                "their_internal_public_key": internalBpublic,
                "our_external_private_key": link.external_private_keyA,
                "their_vpc_address": ipB
            }
    script_paramsB = {
                "my_internal_wg_ip":"192.168.0.3",
                "their_internal_wg_ip": "192.168.0.2",
                "their_external_wg_ip":"192.168.0.5",
                "my_external_wg_ip":"192.168.0.4",
                "our_cidr": link.clientB.cidr,
                "their_cidr": link.clientA.cidr,
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "our_external_port":"3002",
                "my_internal_private_key": internalBprivate,
                "their_internal_public_key": internalApublic,
                "our_external_private_key": link.external_private_keyB,
                "our_clients_public_key": link.clientB.public_key,
                "their_vpc_address": ipA
            }
    instanceA_name = prefix + "a"
    instanceB_name = prefix + "b"
    operationA = controller.create_instance(link.zoneA, instanceA_name, ipA, imageID, vcpus, script, script_paramsA)
    operationB = controller.create_instance(link.zoneB, instanceB_name, ipB, imageID, vcpus, script, script_paramsB)
    controller.wait_for_zone_operation(link.zoneA, operationA['name'])
    controller.wait_for_zone_operation(link.zoneB, operationB['name'])
    # add instances to pools
    instanceA_self_link = "zones/{zone}/instances/{name}".format(zone=link.zoneA, name=instanceA_name)
    instanceB_self_link = "zones/{zone}/instances/{name}".format(zone=link.zoneB, name=instanceB_name)
    controller.add_instance_to_pool(instanceA_self_link, link.poolA, link.regionA)
    controller.add_instance_to_pool(instanceB_self_link, link.poolB, link.regionB)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    parser.add_argument('src', help='region')
    parser.add_argument('dst', help='region')
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)
    build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    gcp = GCPController(config["project"])
    with open(os.path.join(build_dir, config["name"] + ".pickle"), "r") as f:
        links = pickle.load(f)

    try:
        link = next(x for x in links if x.equals(args.src, args.dst))
    except StopIteration as e:
        link = next(x for x in links if x.equals(args.dst, args.src))

    pprint(link.__dict__)
    #expand_link(gcp, link)


