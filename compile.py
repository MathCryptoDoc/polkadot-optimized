#!/usr/bin/env python3

# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

# Script to compile a specific version of polkadot with many different 
# sets of optimization options (specified in the code down below).
#
# The binaries are placed in ~/optimized_polkadot/bin/VERSION
# (change this in the code below if needed).
# Beware that compiling takes a while (about 30 min per set of options).
# It is advisable to run the script in a screen session.

from operator import truediv
import subprocesss
import os
import shutil
import re
import glob
import json
import logging

import datetime
import dateutil.relativedelta
import itertools


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
    os.chdir(os.path.expanduser('~/optimized_polkadot'))
    bin_dir = 'bin/' + version
    if not os.path.isdir(bin_dir):
        os.mkdir(bin_dir)

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
    log_file = os.path.expanduser('~/optimized_polkadot/' + new_filename_root + ".log")

    if os.path.isdir('polkadot'):
        shutil.rmtree('polkadot')

    # Clone git and run init
    work_dir = os.path.expanduser('~/optimized_polkadot')
    run("git clone --depth 1 --branch v{} https://github.com/paritytech/polkadot.git".format(version), work_dir, log_file)

    work_dir = os.path.expanduser('~/optimized_polkadot/polkadot')
    run("./scripts/init.sh", work_dir, log_file)

    # Set build options
    if opts['toolchain'] == 'stable':
        run("rustup override set stable", work_dir, log_file)
    else:
        run("rustup override set nightly", work_dir, log_file)
        # subprocess.Popen("rustup override set nightly", shell=True, check=True, universal_newlines=True)

    run("cargo fetch", work_dir, log_file)

    RUSTFLAGS = "-C opt-level=3"
    if not opts['arch'] == None:
        RUSTFLAGS = RUSTFLAGS + " -C target-cpu={}".format(opts['arch'])
    if opts['codegen']:
        RUSTFLAGS = RUSTFLAGS + " -C codegen-units=1"
    if opts['lto_ldd']:
        RUSTFLAGS = RUSTFLAGS + " -C linker-plugin-lto -C linker=clang -C link-arg=-fuse-ld=lld"
    # Does not work as RUSTFLAGS
    #if opts['lto']:
    #    RUSTFLAGS = RUSTFLAGS + " -C embed-bitcode -C lto=fat"

    # Start building
    cargo_build_opts = ' --profile={} --locked --target=x86_64-unknown-linux-gnu'.format(opts['profile'])
        
    if opts['toolchain'] == 'nightly':
        cargo_build_opts = cargo_build_opts + ' -Z unstable-options'    

    cargo_cmd = 'cargo build ' + cargo_build_opts
    env = os.environ.copy()
    env["RUSTFLAGS"] =  RUSTFLAGS

    dt1 = datetime.datetime.now()
    run(cargo_cmd, work_dir, log_file, env=env)
    dt2 = datetime.datetime.now()

    ## Copy new polkadot file
    os.chdir(os.path.expanduser('~/optimized_polkadot'))

    orig_filename = 'polkadot/target/x86_64-unknown-linux-gnu/{}/polkadot'.format(opts['profile'])
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
    # Change version and options here
    version = '0.9.26'
    
    all_opts_1 = {'toolchain': ['stable', 'nightly'],
                'arch':      [None, 'skylake', 'alderlake'],
                'codegen':   [False, True],
                'lto_ldd':   [False, True],
                'profile':   ['release']
                }

    all_opts_2 = {'toolchain': ['stable', 'nightly'],
                'arch':      [None, 'skylake', 'alderlake'],
                'codegen':   [False, True],
                'lto_ldd':   [False],
                'profile':   ['production']
                }
    # Take all combinations in all_opts_x    
    opts = list(product_dict(**all_opts_1)) + list(product_dict(**all_opts_2))
    print(opts)                            


    # Remark: LTO_LDD is not LTO. Also LTO cannot be given as an option via RUSTFLAGS
    # These options give the following errors:
    # {'toolchain': 'stable', 'arch': None, 'codegen': False, 'lto_ldd': False, 'lto': True, 'profile': 'release'} 
    #   error: lto can only be run for executables, cdylibs and static library outputs
    # {'toolchain': 'nightly', 'arch': None, 'codegen': False, 'lto_ldd': False, 'lto': True, 'profile': 'release'}
    #   error: lto can only be run for executables, cdylibs and static library outputs
    # https://users.rust-lang.org/t/error-lto-can-only-be-run-for-executables-cdylibs-and-static-library-outputs/73369/3
    #
    # However, it is included in Cargo.toml profile
    #  [profile.production]
    #  inherits = "release"
    #  lto = true
    #  codegen-units = 1    
                                    
    print("Number of different builds: {}".format(len(opts)))
    for opt in opts:
        compile(version, opt)        
