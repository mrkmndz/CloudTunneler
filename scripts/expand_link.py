from keygen import keygen
from link import Link, Client
from gcp_controller import GCPController
import time
from pprint import pprint

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
                "our_cidr": link.clientA.cidr,
                "their_cidr": link.clientB.cidr,
                "my_internal_port":"3005",
                "their_internal_port":"3005",
                "our_external_port":"3002",
                "my_internal_private_key": internalAprivate,
                "their_internal_public_key": internalBpublic,
                "our_external_private_key": link.external_private_keyA,
                "our_clients_public_key": link.clientA.public_key,
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
    # create link
    link = Link("proj-204902",
                "us-west1",
                "europe-west2", 
                "from-oregon-to-london",
                "from-london-to-oregon",
                "us-west1-b",
                "europe-west2-a",
                Client("192.168.1.0/24", "PEyAxX9TkfUZL6WtT5Wom/vUBLU58Q+Bm96HOoS8GC8="),
                Client("192.168.2.0/24", "V7Xk17ue208HvTP+HATwbTqCTwl5am10z1TQeIRKmB8="),
                "uAQZLoJJFJfEP7HmHdwhOmIrNaQ5HFtN4bxwOaFw4Gk=",
                # pubkey sSZRAEzYMKv8KVdnXdiKWqRWvK4GvgTog8XgS+yWDBI=
                "eOnUcSdci+B2lTEN+XhATLlU+Jm9TTurePnmXJtKy1k="
                # pubkey vkTIgND+JmGeywcVLowaj4Q2f7CSgr0qhHu6rNbzAw8=
            )

    gcp = GCPController("proj-204902")
    expand_link(gcp, link)


