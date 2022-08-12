# polkadot-optimized --- Optimized binaries for polkadot
A set of scripts to compile, benchmark and analyze different optimization options when compiling polkadot yourself.

## Getting started

### Install Python libraries
Required: python3, pandas, dateutil, request, psutil, pyarrow. This works on Ubuntu 22.04:
```
sudo apt install python3-dateutil python3-requests python3-pandas
pip3 install psutil pyarrow
```

### Install Rust
From https://www.rust-lang.org/tools/install
```
sudo apt install cmake clang lld build-essential git libclang-dev pkg-config libssl-dev 
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  #  Hit enter
source $HOME/.cargo/env
rustup update
```

### Install Docker 
From https://docs.docker.com/engine/install/ubuntu/
```
sudo apt-get install ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### Allow current user to start docker 
From https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user
```
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker 
```

## Compile and analyze

### Get polkadot-optimized
```
git clone https://github.com/MathCryptoDoc/polkadot-optimized.git
cd polkadot-optimized
```

### Start compilation and benchmarking
Modify bottom of ``compile.py`` for desired release version and optimization options. You can also choose a smaller set of options to test.
```
python3 compile.py
python3 run_benchmarks.py
python3 parse_benchmarks.py
```


## Support us

See https://www.math-crypto.com/






