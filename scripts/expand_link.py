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

    rga = link.router_group_a
    rgb = link.router_group_b

    private_ipA = controller.reserve_vpc_ip(rga.region, "int-" + prefix + "a")
    private_ipB = controller.reserve_vpc_ip(rgb.region, "int-" + prefix + "b")
    public_ipA = controller.reserve_vpc_ip(rga.region, "ext-" + prefix + "a", is_internal=False)
    public_ipB = controller.reserve_vpc_ip(rgb.region, "ext-" + prefix + "b", is_internal=False)
    pprint(private_ipA)
    pprint(public_ipA)
    pprint(private_ipB)
    pprint(public_ipB)

    print('Creating instances.')

    #TODO maybe put this somewhere else
    imageID = "just-wireguard"
    vcpus = 4
    script =  "startup-script.py"

    internalApublic, internalAprivate = keygen()
    internalBpublic, internalBprivate = keygen()
    externalApublic, externalAprivate = keygen()
    externalBpublic, externalBprivate = keygen()
    clientsA = json.dumps([c.data() for c in rga.clients])
    clientsB = json.dumps([c.data() for c in rgb.clients])
    script_paramsA = {
                "my_internal_wg_ip": "192.168.0.2",
                "their_internal_wg_ip":"192.168.0.3",
                "their_external_wg_ip":"192.168.0.4",
                "my_external_wg_ip":"192.168.0.5",
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "my_external_port":"3002",
                "my_internal_private_key": internalAprivate,
                "their_internal_public_key": internalBpublic,
                "my_external_private_key": externalAprivate, 
                "their_vpc_address": private_ipB,
                "our_clients": clientsA,
                "their_clients": clientsB
            }
    script_paramsB = {
                "my_internal_wg_ip":"192.168.0.3",
                "their_internal_wg_ip": "192.168.0.2",
                "their_external_wg_ip":"192.168.0.5",
                "my_external_wg_ip":"192.168.0.4",
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "my_external_port":"3002",
                "my_internal_private_key": internalBprivate,
                "their_internal_public_key": internalApublic,
                "my_external_private_key": externalBprivate, 
                "their_vpc_address": private_ipA,
                "our_clients": clientsB,
                "their_clients": clientsA
            }
    instanceA_name = prefix + "a"
    instanceB_name = prefix + "b"
    operationA = controller.create_instance(rga.zone, instanceA_name, private_ipA, public_ipA, imageID, vcpus, script, script_paramsA)
    operationB = controller.create_instance(rgb.zone, instanceB_name, private_ipB, public_ipB, imageID, vcpus, script, script_paramsB)
    controller.wait_for_zone_operation(rga.zone, operationA['name'])
    controller.wait_for_zone_operation(rgb.zone, operationB['name'])

# if __name__ == '__main__':
    # parser = argparse.ArgumentParser(
        # description=__doc__,
        # formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument('config', help='Your tWANg config')
    # parser.add_argument('src', help='region')
    # parser.add_argument('dst', help='region')
    # args = parser.parse_args()

    # with open(args.config, "r") as f:
        # config = json.load(f)
    # build_dir = os.path.join(os.path.dirname(__file__), config["name"] + "-build")
    # gcp = GCPController(config["project"])
    # with open(os.path.join(build_dir, config["name"] + ".pickle"), "r") as f:
        # links = pickle.load(f)

    # try:
        # link = next(x for x in links if x.equals(args.src, args.dst))
    # except StopIteration as e:
        # link = next(x for x in links if x.equals(args.dst, args.src))

    # expand_link(gcp, link)


