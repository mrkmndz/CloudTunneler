# Squid 🦑

Squid is an elastic overlay network built to run on Google Cloud Platform (GCP). 

## Reproduce results from paper
Any machine running code from this repository must have wireguard installed. Follow the instructions here: [https://www.wireguard.com/install/](https://www.wireguard.com/install/).


1. Setup your GCP account.

2. Start a VM on GCP. This VM will be the "controller" and will issue api requests to GCP to create resources necessary for Squid.

3. `ssh` into your controller, clone this repository, and run `./google-setup.bash`

4. Create clients. These can also be provisioned in GCP or elsewhere, but they must have a public IP address and ability to send and receive UDP on any port.

5. Define the topology config file. Or edit one of the existing ones in `scripts/topo-configs` to have the correct IP addresses.

6. Create the topology. `cd scripts` and run `python create_topo.py /path/to/topo/config.json`. Once the script completes, it will create a build directory in the `scripts` directory with the name of your config. You will need this directory to configure your clients. A simple way to distribute it is to commit the directory and later clone it onto the clients.

7. From each client, run `python client-setup.py build/dir/region-client-id.pickle`. This will configure your client with the correct wireguard interfaces. That's it! You can start routing your traffic over Squid.

8. Once you're done, be sure to run the tear down script. `python destroy_topo.py /path/to/topo/config.json`.

## Topology Config
```javascript
{
    "name": "<link-name>", // this will later be the name of the build directory
    "project": "<GCP-project-id>",
    "nodes": [
        {
            "name": "<group-a>",
            "region": "<group-a-gcp-region>",
            "zone": "<group-a-gcp-zone>",
            "clients": [
                {
                    "private_ip": "<new-private-ip>",
                    "public_ip": "<client's-public-ip>"
                }
                // ... more clients if they're closest to <group-a-region>
            ]
        },
        {
            "name": "<group-b>",
            "region": "<group-b-gcp-region>",
            "zone": "<group-b-gcp-zone>",
            "clients": [
                {
                    "private_ip": "<new-private-ip>",
                    "public_ip": "<client's-public-ip>"
                }
                // ... more clients if they're closest to <group-b-region>
            ]
        }
        // ... add more nodes if you have clients in different regions
    ],
    "edges": [
        {
            "from": "<group-a>",
            "to": "<group-b>",
            "width": <n>,
            "internal_tunnel": false // true if you want VPN connections while transiting over GCP
        }
        // ... add more edges to connect the different regions
    ]
}
```