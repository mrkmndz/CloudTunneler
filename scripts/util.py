from collections import namedtuple

def Client(**kwargs):
    C = namedtuple("Client", [
                                "cidr",
                                "public_key"
                            ])
    return C(**kwargs)

def Link(**kwargs):
    L = namedtuple("Link", [
                              "project",
                              "regionA",
                              "regionB",
                              "poolA",
                              "poolB",
                              "zoneA",
                              "zoneB",
                              "clientA",
                              "clientB",
                              "external_private_keyA", # new machine
                              "external_private_keyB" # new machine
                          ])
    return L(**kwargs)

