from keygen import keygen

class Client(object):
    def __init__(self, ip):
        self.ip = ip
        self.public_key, self.private_key = keygen()

class Pool(object):
    def __init__(self, name, ip):
        self.name = name
        self.ip = ip

class RouterGroup(object):
    def __init__(self, region, zone, pool, clients):
        self.region = region
        self.zone = zone
        self.pool = pool
        self.clients = clients
        public_key, private_key = keygen()
        self.client_facing_public_key = public_key
        self.client_facing_private_key = private_key

class Link(object):
    def __init__(self, project, router_group_a, router_group_b):
        self.project = project
        self.router_group_a = router_group_a
        self.router_group_b = router_group_b


