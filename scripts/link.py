from subprocess import call as real_call
import json

def call(*args, **kwargs):
    print args
    real_call(*args, **kwargs)

def keygen():
    call("wg genkey | tee privatekey | wg pubkey > publickey", shell=True)
    with open("privatekey", "r") as f:
        private_key = f.read()
    with open("publickey", "r") as f:
        public_key = f.read()
    call("rm privatekey publickey", shell=True)
    return public_key[:-1], private_key[:-1]

class RouterGroup(object):
    def __init__(self, region, zone, clients):
        self.region = region
        self.zone = zone
        self.clients = clients

class Link(object):
    def __init__(self, project, router_group_a, router_group_b):
        self.project = project
        self.router_group_a = router_group_a
        self.router_group_b = router_group_b
    def equals(self, regiona, regionb):
        return regiona == self.router_group_a.region and regionb == self.router_group_b.region

class Node(object):
    def __init__(self, node_config):
        self.name = node_config["name"]
        self.region = node_config["region"]
        self.zone = node_config["zone"]
        self.clients = [Client(x) for x in node_config["clients"]]
        self.transits = []

class Client(object):
    def __init__(self, client_config):
        self.private_ip = client_config["private_ip"]
        self.public_ip = client_config["public_ip"]
        self.free_port = 5001
        # map from node name to list of tuples of (endpoint, transit)
        self.transits = {}

    def gain_transits_to_node(self, other_node, transits):
        tuples = []
        for transit in transits:
            ep = self.provision_endpoint()
            ep.tunnel_to(transit.add_client(self))
            tuples.append((ep, transit))
        self.transits[other_node.name] = tuples

    def provision_endpoint(self):
        ep = Endpoint(self.public_ip, self.free_port)
        self.free_port += 1
        return ep

class Transit(object):
    def __init__(self, client_facing_ip, vpc_ip, private_ip_a, private_ip_b, internal_tunnel):
        self.client_facing_ip = client_facing_ip
        self.vpc_ip = vpc_ip
        self.private_ip_a = private_ip_a
        self.private_ip_b = private_ip_b
        self.free_port = 5001
        self.transit_facing_endpoint = Endpoint(self.vpc_ip, 3001)
        # list of tuples of (endpoint, client)
        self.client_facing_endpoints = []
        self.pair = None
        self.internal_tunnel = internal_tunnel

    # returns endpoint that the client should tunnel to
    def add_client(self, client):
        ep = self.provision_client_endpoint()
        self.client_facing_endpoints.append((ep, client))
        return ep

    def provision_client_endpoint(self):
        ep = Endpoint(self.client_facing_ip, self.free_port)
        self.free_port += 1
        return ep
    
    def pair_with(self, pair_transit):
        if self.pair is not None:
            raise Exception("transit already has a pair")
        if pair_transit.pair is not None:
            raise Exception("pair transit already has a pair")
        self.pair = pair_transit
        pair_transit.pair = self
        pair_transit.transit_facing_endpoint.tunnel_to(self.transit_facing_endpoint)

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


class Endpoint(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.public_key, self.private_key = keygen()
        self.partner = None
    def tunnel_to(self, endpoint, should_recurse=True):
        if self.partner is not None:
            raise Exception("endpoint already has a partner")
        self.partner = endpoint
        if (should_recurse):
            endpoint.tunnel_to(self, should_recurse=False)
    def create_wireguard_config(self):
        conf_str = "[Interface]\n"
        conf_str += "PrivateKey = %s\n" % self.private_key
        conf_str += "ListenPort = %s\n" % self.port
        conf_str += "[Peer]\n"
        conf_str += "PublicKey = %s\n" % self.partner.public_key
        conf_str += "Endpoint = %s:%d\n" % (self.partner.ip, self.partner.port)
        conf_str += "AllowedIPs = 0.0.0.0/0\n"
        return conf_str
    def realize(self, own_virtual_ip):
        if_name = alloc_if_name()
        with open(if_name + ".conf", "w+") as f:
            f.write(self.create_wireguard_config())
        start_wg_interface(own_virtual_ip, if_name)
        return if_name

