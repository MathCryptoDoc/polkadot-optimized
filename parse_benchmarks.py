#!/usr/bin/env python3

# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

# Script to parse the benchmark files that were generated
# by run_benchmarks.py. It will read all the files in
#   ~/polkadot-optimized/output/VERSION/HOSTNAME/DATE_TIME/
# For each combination of VERSION, HOSTNAME, DATE_TIME a 
# pandas dataframe is constructed and stored in
#   ~/polkadot-optimized/processed/todo/
# as a feather object and 
#   ~/polkadot-optimized/processed/csv/
# as a csv file. Processed files are then moved to 
#   ~/polkadot-optimized/processed/old/


import re
import pandas as pd
import os
from glob import glob
import shutil
import json
# pip install pyarrow
from datetime import datetime
from pathlib import Path

def convert_to_MiB(score_string):
    raw_nb = float(re.findall("[+-]?\d+\.\d+", score_string)[0])
    if 'KiB/s' in score_string:
        nb = raw_nb/1000
    if 'MiB/s' in score_string:
        nb = raw_nb
    if 'GiB/s' in score_string:    
        nb = raw_nb*1000            
    return nb

def get_cpu_pct(bench):
    cpu_start = -1
    cpu_end = -1
    for line in filter(None, bench.split('\n')):

        if not line.startswith('CPU'):
            continue
        if cpu_start==-1:
            cpu_start = float(line.split(':')[-1])
        else:
            cpu_end = float(line.split(':')[-1])
    return max(cpu_start, cpu_end)

# https://stackoverflow.com/questions/19127704/how-to-read-ascii-formatted-table-in-python
def get_scores(ascii_table):
    header = []
    scores = []
    for line in filter(None, ascii_table.split('\n')):
        if not line.startswith('|'):
            continue
        if '-+-' in line or '===' in line:
            continue
        if not header:            
            header = line.split('|')[1:-1]            
            continue                
        splitted_line = line.split('|')[1:-1]                
        score_string = splitted_line[2]        
        scores.append( convert_to_MiB(score_string) )
    return scores

def get_extrinsic_times(output_text):
    times = {}
    times['tot'] = float(re.search('(?<=Total: )(\d+)', output_text).group(0))
    times['min'] = float(re.search('(?<=Min: )(\d+)', output_text).group(0))
    times['max'] = float(re.search('(?<=Max: )(\d+)', output_text).group(0))
    times['avg'] = float(re.search('(?<=Average: )(\d+)', output_text).group(0))
    times['med'] = float(re.search('(?<=Median: )(\d+)', output_text).group(0))
    times['std'] = float(re.search('(?<=Stddev: )(\d+)', output_text).group(0))
    pct_99_95_75 = re.search('(?<=Percentiles 99th, 95th, 75th: )(\d+), (\d+), (\d+)', output_text).group(0).split(",")
    times['pct99'] = float(pct_99_95_75[0])
    times['pct95'] = float(pct_99_95_75[1])
    times['pct75'] = float(pct_99_95_75[2])
    return times


def parse():
    output_dir = Path("output")
    processed_dir = Path("processed")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(processed_dir / "csv", exist_ok=True)   
    os.makedirs(processed_dir / "todo", exist_ok=True)
    os.makedirs(processed_dir / "old", exist_ok=True)   
    
    path_version_date_host = output_dir.glob("*/*/*")  
    for p in path_version_date_host:        
        version = p.parts[1]
        host = p.parts[2]        
        date = p.parts[3]            

        # read all build json files
        build_info = {}
        for f in p.glob('bench_*.json'):            
            nb_build = f.stem.split("_")[1]            
            with open(f, "r") as text_file:
                build_info[nb_build] = json.load(text_file)['build_options']  
                # Booleans are not stored in pyarrow -- ugly translation to string
                for key, value in build_info[nb_build].items():              
                    if key=='lto' and value==False:
                        build_info[nb_build]['lto'] = 'False'
        # [profile.release]
        # # Polkadot runtime requires unwinding.
        # panic = "unwind"
        # opt-level = 3   
        # https://doc.rust-lang.org/rustc/codegen-options/index.html#codegen-units
        # The default value, if not specified, is 16 for non-incremental builds.  
        # https://doc.rust-lang.org/rustc/codegen-options/index.html#lto
        # If -C lto is not specified, then the compiler will attempt to perform "thin local LTO" 
        # which performs "thin" LTO on the local crate only across its codegen units.            
        build_info['official'] = { "toolchain": "nightly", "arch": "none", "codegen-units": 16,
                                    "lto": "thin local", "opt-level": 3 }
        build_info['docker'] = build_info['official']   
                
        # read the benchmarks
        all_data = []        
        for f in p.glob('bench_*.txt'):               
            nb_build = f.stem.split("_")[1]            
            nb_run = int(f.stem.split("_")[3])            
            ts = int(os.path.getmtime(f))            
            # date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d_%Hh%Mm')
                                    
            with open(f, "r") as text_file:
                bench = text_file.read()
                scores = get_scores(bench) 

                if not scores: 
                    # no benchmark table (arch not supported probably)
                    continue
                 
                data = {"host": host, "date": date,                   
                    "ver": version,
                    "nb_run": nb_run, "nb_build": nb_build,                      
                    "cpu": get_cpu_pct(bench),
                    "BLAKE2-256": scores[0], "SR25519-Verify": scores[1],
                    "Copy": scores[2],
                    "Seq_Write": scores[3], "Rnd_Write": scores[4]}
                data.update(build_info[nb_build])    
                
                if not all_data:
                    all_data = [data]
                else:
                    all_data.append(data)

        # save as dataframe
        df = pd.DataFrame(all_data).reset_index()            
        df.to_csv(processed_dir / "csv" / "{}_{}_{}.csv".format(version, host, date), index=False)
        df.to_feather(processed_dir / "todo" / "{}_{}_{}.feather".format(version, host, date))        
        print(df)        

        # read the signing extrinsic
        all_data = []        
        for f in p.glob('new_bench_*.txt'):               
            nb_build = f.stem.split("_")[2]            
            nb_run = int(f.stem.split("_")[4])            
            ts = int(os.path.getmtime(f))            
            # date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d_%Hh%Mm')
                                    
            with open(f, "r") as text_file:
                bench = text_file.read()
                times = get_extrinsic_times(bench) 

                if not times: 
                    # no benchmark table (arch not supported probably)
                    continue
                 
                data = {"host": host, "date": date,                   
                    "ver": version,
                    "nb_run": nb_run, "nb_build": nb_build,                      
                    "cpu": get_cpu_pct(bench)}
                data.update(times)                            
                data.update(build_info[nb_build])    
                
                if not all_data:
                    all_data = [data]
                else:
                    all_data.append(data)

        # save as dataframe
        df = pd.DataFrame(all_data).reset_index()                  
        df.to_csv(processed_dir / "csv" / "extrinsic_{}_{}_{}.csv".format(version, host, date), index=False)
        df.to_feather(processed_dir / "todo" / "extrinsic_{}_{}_{}.feather".format(version, host, date))        
        print(df)

        shutil.move(p, processed_dir / "old" / version / host / date) 
        
        # TODO remove dir if empty with bench

        

if __name__=="__main__":
    parse()


