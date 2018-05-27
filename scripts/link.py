class Client(object):
    def __init__(self, cidr, public_key):
        self.cidr = cidr
        self.public_key = public_key

class Link(object):
    def __init__(self, project, regionA, regionB,
                poolA, poolB, zoneA, zoneB, clientA, clientB, external_private_keyA, external_private_keyB):
        self.project = project
        self.regionA = regionA
        self.zoneA = zoneA
        self.poolA = poolA
        self.clientA = clientA
        self.regionB = regionB
        self.zoneB = zoneB
        self.poolB = poolB
        self.clientB = clientB
        self.external_private_keyA = external_private_keyA
        self.external_private_keyB = external_private_keyB


