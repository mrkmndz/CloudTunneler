from keygen import keygen
import json

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

class Client(object):
    def __init__(self, client_config):
        self.private_ip = client_config["private_ip"]
        self.public_ip = client_config["public_ip"]
        self.free_port = 5001
        # map from node name to list of transits
        self.transits = {}

    def gain_transits_to_node(self, other_node, transits):
        for transit in transits:
            ep = self.add_endpoint()
            ep.tunnel_to(transit.add_client_endpoint())
        self.transits[other_node.name] = transits

    def add_endpoint(self):
        ep = Endpoint(self.public_ip, self.free_port)
        self.endpoints.append(ep)
        self.free_port += 1
        return ep

class Transit(object):
    def __init__(self, client_facing_ip, vpc_ip, private_ip_a, private_ip_b):
        self.client_facing_ip = client_facing_ip
        self.vpc_ip = vpc_ip
        self.private_ip_a = private_ip_a
        self.private_ip_b = private_ip_b
        self.free_port = 5001
        self.transit_facing_endpoint = Endpoint(self.vpc_ip, 3001)
        self.client_facing_endpoints = []

    def add_client_endpoint(self, client_endpoint):
        ep = Endpoint(self.client_facing_ip, self.free_port)
        self.client_facing_endpoints.append(ep)
        self.free_port += 1
        return ep
    
    def pair(self, pair_transit):
        if self.pair:
            raise Exception("transit already has a pair")
        pair_transit.transit_facing_endpoint.tunnel_to(self.transit_facing_endpoint)
        self.pair = pair_transit


class Endpoint(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.public_key, self.private_key = keygen()
    def tunnel_to(endpoint):
        if self.partner:
            raise Exception("endpoint already has a partner")
        self.partner = endpoint
        endpoint.tunnel_to(self)
