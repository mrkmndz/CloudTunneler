#! /usr/bin/python
import requests
import sys
import pickle
from link import *

def main():
    # send output to file
    sys.stdout = open("startup-script.out", "w+")
    sys.stderr = open("startup-script.out", "w+")

    serialized = requests.get("http://metadata/computeMetadata/v1/instance/attributes/me",
                                            headers={"Metadata-Flavor": "Google"}).text
    me = pickle.loads(serialized)

    # allow ip forwarding
    call("sudo sysctl -w net.ipv4.ip_forward=1", shell=True)

    for endpoint, client in me.client_facing_endpoints:
        if_name = endpoint.realize(me.private_ip_a)
        call("sudo ip route add %s dev %s" % (client.private_ip, if_name), shell=True) 
    
    transit_if_name = me.transit_facing_endpoint.realize(me.private_ip_b)
    for endpoint, client in me.pair.client_facing_endpoints:
        call("sudo ip route add %s dev %s" % (client.private_ip, transit_if_name), shell=True) 

    call("sudo ip route add %s dev %s" % (me.pair.private_ip_a, transit_if_name), shell=True) 
    call("sudo ip route add %s dev %s" % (me.pair.private_ip_b, transit_if_name), shell=True) 

    sys.stdout.close()
    sys.stderr.close()

if __name__ == '__main__':
    main()

