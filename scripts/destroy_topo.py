import argparse
import json
from gcp_controller import GCPController

def main(config_file):
    with open(config_file, "r") as f:
        config = json.load(f)
    gcp = GCPController(config["project"])
    for region in config["regions"]:
        # delete forwarding rules
        gcp.delete_all(gcp.compute.forwardingRules(), "forwardingRule", region["name"])
        # delete ip address
        gcp.delete_all(gcp.compute.addresses(), "address", region["name"])
        # delete pools
        gcp.delete_all(gcp.compute.targetPools(), "targetPool", region["name"])
        # delete instances
        gcp.delete_all_instances(region["zone"])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='Your tWANg config')
    args = parser.parse_args()
    main(args.config)
