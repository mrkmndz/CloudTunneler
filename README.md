# Squid 🦑

Squid is an elastic overlay network built to run on Google Cloud Platform (GCP). 

## Reproduce results from paper
Any machine running code from this repository must have wireguard installed. Follow the instructions here: [https://www.wireguard.com/install/](https://www.wireguard.com/install/). 

1. Setup your GCP account and create a project where Squid will run.

2. You must create a new image on GCP to allow Squid to configure transit machines. Do this by launching CentOS version "CentOS Linux release 7.5.1804 (Core)". Then clone this repository into the root directory and install wireguard with `./wireguard-setup.bash`. Once all the installation is complete, stop the VM and create an image in the GCP web interface. Be sure to name this image "prepped".

3. Start a VM on GCP (it is convenient to use "prepped" image). This VM will be the "controller" and will issue api requests to GCP to create resources necessary for Squid.

4. `ssh` into your controller, clone this repository, and run `./google-setup.bash`

5. Create clients. These can also be provisioned in GCP or elsewhere, but they must have a public IP address and ability to send and receive UDP on any port.

6. Define the topology config file. Or edit one of the existing ones in `scripts/topo-configs` to have the correct IP addresses.

7. Create the topology. `cd scripts` and run `python create_topo.py /path/to/topo/config.json`. Once the script completes, it will create a build directory in the `scripts` directory with the name of your config. You will need this directory to configure your clients. A simple way to distribute it is to commit the directory and later clone it onto the clients.

8. From each client, run `python client-setup.py build/dir/region-client-id.pickle`. This will configure your client with the correct wireguard interfaces. That's it! You can start routing your traffic over Squid.

9. Once you're done, be sure to run the tear down script. `python destroy_topo.py /path/to/topo/config.json`.

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