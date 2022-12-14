#!/usr/bin/env python3

# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

# Script to benchmark many different polkadot binaries that were 
# compiled using compile.py. Version needs to be specified in
# the code below. Binaries are expected to placed in
#     ~/polkadot-optimized/bin/VERSION
# The output of the benchmarks are placed in 
#     ~/polkadot-optimized/output/VERSION/HOSTNAME/DATE_TIME
# Both directories are hard-codes so change this in the code 
# below if needed.
#
# Beware that benchmarking takes a while!
# It is advisable to run the script in a screen session.
#
# Docker needs to be runnable without sudo privileges!

import subprocess
import sys
import os, stat
import socket
from datetime import datetime
import psutil # pip install psutil
import glob
import re
import shutil
from pathlib import Path
import requests


def perform_benchmark(binary, NB_RUNS, nb_build, processed_dir, docker=False):
    for i in range(NB_RUNS):        
        print("Performing benchmark run {} for polkadot build {}".format(i, nb_build))

        pct_before = psutil.cpu_percent(interval=2)
        if not docker:
            bench = subprocess.run([binary, "benchmark", "machine", "--disk-duration", "30"], 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)                    
        else:
            #shlex.split("docker run --rm -it parity/polkadot:v0.9.26 benchmark machine --disk-duration 30")
            bench = subprocess.run(['docker', 'run', '--rm', '-it', 'parity/polkadot:v{}'.format(version), 
                                    'benchmark', 'machine', '--disk-duration', '30'], 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)                    
        out = bench.stdout.decode("utf-8")
        pct_after = psutil.cpu_percent(interval=2)

        with open(processed_dir + "/bench_{}_run_{}.txt".format(nb_build, i), "w") as text_file:
            text_file.write("CPU utilization at start: {}\n".format(pct_before))
            text_file.write(out)
            text_file.write("CPU utilization at end: {}\n".format(pct_after))

    # TODO test for version >= 0.9.27
    # TODO number of tests i hard coded (idea: take 1/5 of NB_RUNS)
    for i in range(4):        
        print("Performing extrinsic benchmark run {} for polkadot build {}".format(i, nb_build)) 

        pct_before = psutil.cpu_percent(interval=2)
        if not docker:
            bench = subprocess.run([binary, 'benchmark', 'extrinsic', '--pallet', 'system', '--extrinsic', 'remark', '--chain', 'polkadot-dev'], 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)                    
        else:
            #shlex.split("docker run --rm -it parity/polkadot:v0.9.26 benchmark machine --disk-duration 30")
            bench = subprocess.run(['docker', 'run', '--rm', '-it', 'parity/polkadot:v{}'.format(version), 
                                    'benchmark', 'extrinsic', '--pallet', 'system', '--extrinsic', 'remark', '--chain', 'polkadot-dev'], 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)                    
        out = bench.stdout.decode("utf-8")
        pct_after = psutil.cpu_percent(interval=2)

        with open(processed_dir + "/new_bench_{}_run_{}.txt".format(nb_build, i), "w") as text_file:
            text_file.write("CPU utilization at start: {}\n".format(pct_before))
            text_file.write(out)
            text_file.write("CPU utilization at end: {}\n".format(pct_after))

def run(version, NB_RUNS = 5):
    os.chdir(os.path.expanduser('~/polkadot-optimized'))
    bin_dir = 'bin/' + version
    list_of_files = glob.glob(bin_dir + '/polkadot_*.bin')

    # Prepare output directory    
    host = socket.gethostname()    
    now = datetime.now().strftime("%Y-%b-%d_%Hh%M")
    processed_dir = 'output/' + version + "/" + host + "/" + now
    if not os.path.isdir(processed_dir):
        os.makedirs(processed_dir)

    # Run all numbered binaries polkadot_NB.bin
    for binary in list_of_files:
        nb = int(re.findall("_\d+.bin",binary)[0][1:-4])        
        perform_benchmark(binary, NB_RUNS, nb, processed_dir)
        # Copy json build file
        orig_json = binary[:-4] + '.json'
        new_json = processed_dir + '/bench_{}.json'.format(nb)
        shutil.copy2(orig_json, new_json)

    # Run official binary    
    binary = bin_dir + '/official_polkadot.bin'
    if not os.path.exists(binary):
        print("Dowloading polkadot binary since official_polkadot.bin not found.")
        url = "https://github.com/paritytech/polkadot/releases/download/v{}/polkadot".format(version) 
        resp = requests.get(url)
        with open(binary, "wb") as f: # opening a file handler to create new file 
            f.write(resp.content)
    if not os.access(binary, os.X_OK):
        print("Setting executable permission for official_polkadot.bin.")
        os.chmod(binary, stat.S_IXUSR)
    perform_benchmark(binary, NB_RUNS, "official", processed_dir)

    # Run in Docker    
    perform_benchmark(None, NB_RUNS, "docker", processed_dir, docker=True)
    # sudo docker run --rm -it parity/polkadot:vVER benchmark machine --disk-duration 30

        

    

if __name__=="__main__":
    # Change version here
    version = "0.9.27"    
    NB_RUNS = 20
    # For testing:
    # NB_RUNS = 2
    run(version, NB_RUNS)
    
    
