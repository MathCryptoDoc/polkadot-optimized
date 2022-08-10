#!/usr/bin/env python3

# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

# Script to benchmark many different polkadot binaries that were 
# compiled using compile.py. Version needs to be specified in
# the code below. Binaries are expected to placed in
#     ~/polkadot_optimized/bin/VERSION
# The output of the benchmarks are placed in 
#     ~/polkadot_optimized/output/VERSION/HOSTNAME/DATE_TIME
# Both directories are hard-codes so change this in the code 
# below if needed.
#
# Beware that benchmarking takes a while!
# It is advisable to run the script in a screen session.
#
# Docker needs to be runnable without sudo privileges!

import subprocess
import sys
import os
import socket
from datetime import datetime
import psutil # pip install psutil
import glob
import re
import shutil
from pathlib import Path

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

def run(version, NB_RUNS = 5):
    os.chdir(os.path.expanduser('~/polkadot_optimized'))
    bin_dir = 'bin/' + version
    list_of_files = glob.glob(bin_dir + '/polkadot_*.bin')

    # Prepare output directory    
    host = socket.gethostname()    
    now = datetime.now().strftime("%Y-%b-%d_%Hh%M")
    processed_dir = 'output/' + version + "/" + host + "/" + now
    if not os.path.isdir(processed_dir):
        os.makedirs(processed_dir)

    # # Run all numbered binaries polkadot_NB.bin
    for binary in list_of_files:
        nb = int(re.findall("_\d+.bin",binary)[0][1:-4])        
        perform_benchmark(binary, NB_RUNS, nb, processed_dir)
        # Copy json build file
        orig_json = binary[:-4] + '.json'
        new_json = processed_dir + '/bench_{}.json'.format(nb)
        shutil.copy2(orig_json, new_json)

    # Run official binary
    binary = bin_dir + '/official_polkadot.bin'
    perform_benchmark(binary, NB_RUNS, "official", processed_dir)

    # Dockerele    
    perform_benchmark(None, NB_RUNS, "docker", processed_dir, docker=True)
    

if __name__=="__main__":
    # Change version here
    version = "0.9.26"
    NB_RUNS = 20
    run(version, NB_RUNS)
    
    
