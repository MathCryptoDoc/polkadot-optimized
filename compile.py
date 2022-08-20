#!/usr/bin/env python3

# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

# Script to compile a specific release of polkadot with many different 
# sets of optimization options (specified in the code down below, look
# for the ##########).
#
# The binaries are placed in 
#     ~/polkadot-optimized/bin/VERSION
# (change this in the code below if needed).
# Beware that compiling takes a while (about 30 min per set of options).
# It is recommended to run the script in, for example, a screen session.

from operator import truediv
import subprocess
import os
import shutil
import re
import glob
import json
import logging

import datetime
import dateutil.relativedelta
import itertools

import tomlkit
from pathlib import Path

def extract_largest_number(files):    
    if len(files) == 0:        
        return -1
    else:        
        return max([int(re.findall("_\d+.bin",f)[0][1:-4]) for f in files])
    
def hours_minutes(dt1, dt2):
    rd = dateutil.relativedelta.relativedelta(dt2, dt1)
    return "{}H {}M {}S".format(rd.hours, rd.minutes, rd.seconds)

def run(cmd, work_dir, log_file, env=None):    
    os.chdir(work_dir)    
    with open(log_file, "a+") as log:
        if env==None:
            subprocess.run(cmd, shell=True, check=True, universal_newlines=True, stderr=log)
        else:
            subprocess.run(cmd, shell=True, check=True, universal_newlines=True, stderr=log, env=env)        

def compile(version, opts):
    print(" === STARTING COMPILATION === ")
    print(opts)
    print(version)  

    # Prepare build directory
    os.chdir(os.path.expanduser('~/polkadot-optimized'))
    bin_dir = 'bin/' + version
    if not os.path.isdir(bin_dir):
        os.makedirs(bin_dir)

    # Check if opts was not compiled before
    list_of_files = glob.glob(bin_dir + '/polkadot_*.json')
    for f in list_of_files:
        with open(f, "r") as file: 
            json_dict = json.load(file)
            if json_dict['build_options']==opts:
                return
    
    # Get number of new polkadot build, set filenames
    list_of_files = glob.glob(bin_dir + '/polkadot_*.bin')
    nb = extract_largest_number(list_of_files) + 1

    new_filename_root = bin_dir + '/polkadot_{}'.format(nb)
    log_file = os.path.expanduser('~/polkadot-optimized/' + new_filename_root + ".log")

    if os.path.isdir('polkadot'):
        shutil.rmtree('polkadot')

    # Clone git and run init
    work_dir = os.path.expanduser('~/polkadot-optimized')
    run("git clone --depth 1 --branch v{} https://github.com/paritytech/polkadot.git".format(version), work_dir, log_file)

    work_dir = os.path.expanduser('~/polkadot-optimized/polkadot')
    run("./scripts/init.sh", work_dir, log_file)

    # Set build options
    if opts['toolchain'] == 'stable':
        run("rustup override set stable", work_dir, log_file)
    else:
        run("rustup override set nightly", work_dir, log_file)
        # subprocess.Popen("rustup override set nightly", shell=True, check=True, universal_newlines=True)

    run("cargo fetch", work_dir, log_file)

    ## OLD CODE WITH RUSTFLAGS
    # RUSTFLAGS = "-C opt-level=3"
    # if not opts['arch'] == None:
    #     RUSTFLAGS = RUSTFLAGS + " -C target-cpu={}".format(opts['arch'])
    # if opts['codegen']:
    #     RUSTFLAGS = RUSTFLAGS + " -C codegen-units=1"
    # if opts['lto_ldd']:
    #     RUSTFLAGS = RUSTFLAGS + " -C linker-plugin-lto -C linker=clang -C link-arg=-fuse-ld=lld"
    # # Does not work
    # #if opts['lto']:
    # #    RUSTFLAGS = RUSTFLAGS + " -C embed-bitcode -C lto=fat"

    # # Start building
    # cargo_build_opts = ' --profile={} --locked --target=x86_64-unknown-linux-gnu'.format(opts['profile'])

    ## NEW CODE AS CUSTOM PROFILE (
    # It overwrites the production profile -- otherwise still build errors.
    config = tomlkit.loads(Path(work_dir + "/Cargo.toml").read_text())    
    profile = {}
    # TODO test if arch can be set here
    # if not opts['arch'] == None:
    #     profile['arch'] = opts['arch']    
    profile['inherits'] = 'release'    
    profile['codegen-units'] = opts['codegen-units']    
    profile['lto'] = opts['lto']    
    profile['opt-level'] = opts['opt-level']          

    config['profile']['production'] = profile
    with Path(work_dir + "/Cargo.toml").open("w") as fout:
        fout.write(tomlkit.dumps(config))
    
    RUSTFLAGS = ""
    # TODO test if arch can be set in profile
    if not opts['arch'] == None:
        RUSTFLAGS = RUSTFLAGS + " -C target-cpu={}".format(opts['arch'])

    # Start building
    cargo_build_opts = ' --profile=production --locked --target=x86_64-unknown-linux-gnu'    
        
    if opts['toolchain'] == 'nightly':
        cargo_build_opts = cargo_build_opts + ' -Z unstable-options'    

    cargo_cmd = 'cargo build ' + cargo_build_opts
    env = os.environ.copy()
    env["RUSTFLAGS"] =  RUSTFLAGS

    dt1 = datetime.datetime.now()
    run(cargo_cmd, work_dir, log_file, env=env)
    dt2 = datetime.datetime.now()

    ## Copy new polkadot file
    os.chdir(os.path.expanduser('~/polkadot-optimized'))

    orig_filename = 'polkadot/target/x86_64-unknown-linux-gnu/production/polkadot'
    shutil.copy2(orig_filename, new_filename_root + ".bin")

    json_dict = {}
    json_dict['build_options'] = opts
    json_dict['build_time'] = hours_minutes(dt1, dt2)
    json_dict['RUSTFLAGS'] = RUSTFLAGS
    json_dict['build_command'] = cargo_cmd

    json_object = json.dumps(json_dict, indent=4)
    with open(new_filename_root + ".json", "w") as outfile:
        outfile.write(json_object)

# https://stackoverflow.com/questions/5228158/cartesian-product-of-a-dictionary-of-lists
def product_dict(**kwargs):
    keys = kwargs.keys()
    vals = kwargs.values()
    for instance in itertools.product(*vals):
        yield dict(zip(keys, instance))

if __name__ == "__main__":
    version = '0.9.27'

    # # All the options tested for analysis on websise
    # dict_opts = {'toolchain': ['stable', 'nightly'],
    #             'arch':      [None, 'alderlake'],  # use native if other arch
    #             'codegen-units':   [1, 16],
    #             'lto':       ['off', 'fat', 'thin'],                
    #             'opt-level': [2, 3]
    #             } 
    # opts = list(product_dict(**dict_opts))                                      
    
    # Only the good builds after analysis - takes about 3 hours to build
    opts = []
    opts.append({'toolchain': 'stable',  'arch': 'native', 'codegen-units': 1,  'lto': 'fat',  'opt-level': 3}) # build 15
    opts.append({'toolchain': 'stable',  'arch': 'native', 'codegen-units': 16, 'lto': 'fat',  'opt-level': 3}) # build 21
    opts.append({'toolchain': 'nightly', 'arch': 'native', 'codegen-units': 1,  'lto': 'fat',  'opt-level': 2}) # build 38
    opts.append({'toolchain': 'nightly', 'arch': 'native', 'codegen-units': 1,  'lto': 'thin', 'opt-level': 2}) # build 40
    opts.append({'toolchain': 'nightly', 'arch': 'native', 'codegen-units': 16, 'lto': 'fat',  'opt-level': 3}) # build 45
                        
    print("Number of different builds: {}".format(len(opts)))
    for opt in opts:
        compile(version, opt)    