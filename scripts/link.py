from keygen import keygen
import json

class Client(object):
    def __init__(self, ip):
        self.ip = ip
        self.public_key, self.private_key = keygen()

    def data(self):
        return {"ip": self.ip,
            "public_key": self.public_key,
            "private_key": self.private_key}

class RouterGroup(object):
    def __init__(self, region, zone, clients):
        self.region = region
        self.zone = zone
        self.clients = clients
        public_key, private_key = keygen()
        self.client_facing_public_key = public_key
        self.client_facing_private_key = private_key

class Link(object):
    def __init__(self, project, router_group_a, router_group_b):
        self.project = project
        self.router_group_a = router_group_a
        self.router_group_b = router_group_b
    def equals(self, regiona, regionb):
        return regiona == self.router_group_a.region and regionb == self.router_group_b.region


