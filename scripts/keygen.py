from subprocess import call
def keygen():
    call("wg genkey | tee privatekey | wg pubkey > publickey", shell=True)
    with open("privatekey", "r") as f:
        private_key = f.read()
    with open("publickey", "r") as f:
        public_key = f.read()
    call("rm privatekey publickey", shell=True)
    return public_key[:-1], private_key[:-1]
