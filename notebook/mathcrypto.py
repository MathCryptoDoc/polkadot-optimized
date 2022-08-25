# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

import math
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib 
from paretoset import paretoset

# Nice boxplot with x axis sorted according to median
def boxplot_sorted(df, by, column, ax, ascending=True):
    boxprops = dict(linewidth=1.5,color='darkblue')
    medianprops = dict(linewidth=2, color='firebrick')
    
    df2 = pd.DataFrame({col:vals[column] for col, vals in df.groupby(by)})
    meds = df2.median().sort_values(ascending=ascending)        
    df2[meds.index].boxplot(rot=90, ax=ax, boxprops=boxprops, medianprops=medianprops)
    
    
# https://www.tutorialspoint.com/how-to-annotate-the-points-on-a-scatter-plot-with-automatically-placed-arrows-in-matplotlib
def labelled_scatter_plot(df, x_col, y_col, labels_to_plot):
    fig, ax = plt.subplots(1, figsize=(7.5, 5))
    plt.rcParams["figure.figsize"] = [7.00, 5.50]
    plt.rcParams["figure.autolayout"] = True
    
    xpoints = df[x_col]
    ypoints = df[y_col]
    labels = df.index 
    
    plt.scatter(xpoints, ypoints)
    
    ii = 0
    # angles
    ts = np.linspace(0,2*math.pi,int(len(labels_to_plot)*3))
    np.random.seed(1)
    np.random.shuffle(ts)
    xts = np.cos(ts)
    yts = np.sin(ts)
    for label, x, y in zip(labels, xpoints, ypoints):
        if label in labels_to_plot:
            plt.annotate(
              label,
              xy=(x, y), xytext=(xts[ii]*60, yts[ii]*60),
              textcoords='offset points', va='center', ha='center',
              bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.5),
              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
            ii = ii + 1
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.show()
    return fig    

def load_clean_benchmark(path, extrinsic=False):
    "Load the output bench files. The extrinsic is only Remark (for now)."
    df = pd.read_feather(path)
    df['arch'] = df['arch'].fillna('none')
    df['host'] = df['host'].astype('category')
    df['arch'] = df['arch'].astype('category')
    df['ver'] = df['ver'].astype('category')
    df['date'] = df['date'].astype('category')
    df['codegen-units'] = df['codegen-units'].astype('int') # 1 or 16
    df['lto'] = df['lto'].astype('category') # off, False, thin, fat
    df['nb_run'] = df['nb_run'].astype('int')
    df['opt-level'] = df['opt-level'].astype('int')  # 2 or 3
    
    if not extrinsic:
        df['SR25519-Verify'] = df['SR25519-Verify']*1000 # same as in benchmark palette
    else:
        df = df.rename(columns={'med': 'Extr-Remark'})
        df = df.rename(columns={'std': 'Extr-Remark-Std'})
    return df

def load_both_benchmarks(path):
    "Load .feather file with benchmark results and its intrinsic (Remark) counterpart"
    "Usage: (df, df_ex) = load_both_benchmarks('processed/todo/0.9.27_host-Aug-23_09h37.feather')"    
    df = load_clean_benchmark(path, extrinsic=False)
    print("Max CPU is {}%".format(max(df.loc[:,"cpu"])))
    extr_path = "/".join(path.split("/")[0:-1]) + "/extrinsic_"+ path.split("/")[-1]
    df_ex = load_clean_benchmark(extr_path, extrinsic=True)
    print("Max CPU is {}%".format(max(df_ex.loc[:,"cpu"])))
    return (df,df_ex)

def calc_stats(df, score, extrinsic=False):
    if not extrinsic:
        # there is a lot variability on the cpu score 
        # so we take a median and calculate standard error assuming normality
        stats = df[["nb_build", score]].groupby("nb_build")[score].agg(['median', 'mean', 'sem'])
        stats['± mean'] = 1.96 * stats['sem'] # 95% CI
        stats['± median'] = 1.25 * stats['± mean'] 
        sum_stats = stats[["median", "± median"]]
        sum_stats = sum_stats.rename(columns={"median": score, "± median": "Δ-" + score})
    else: 
        # extrinsic benchmark already do their own repititions
        # we take over the median and std error of one run
        stats = df[df["nb_run"]==0][["nb_build", "Extr-Remark", "Extr-Remark-Std"]]
        # N=100 -- TODO extract from bench file
        N = 100.0
        stats['sem'] = stats["Extr-Remark-Std"]/np.sqrt(N)
        stats['± mean'] = 1.96 * stats['sem'] # 95% CI
        stats['± median'] = 1.25 * stats['± mean'] 
        sum_stats = stats[["nb_build", "Extr-Remark", "± median"]]
        sum_stats = sum_stats.rename(columns={"± median": "Δ-" + score})
        sum_stats = sum_stats.set_index("nb_build")
    return sum_stats

def calc_medians_df_df_ex(df, scores, df_ex, extr):
    "Assemble one dataframe with scores (array) from df and extr (array) from df_ex"
    stats = []
    for s in scores:
        stats.append(calc_stats(df, s))
    for e in extr:
        stats.append(calc_stats(df_ex, e, extrinsic=True))
    medians = pd.concat(stats, axis=1)
    return medians

def find_exact_pareto(medians, scores, extrinsics):
    sense = ["max"] * len(scores) + ["min"] * len(extrinsics)
    mask = paretoset(medians[scores+extrinsics], sense=sense)
    pareto = medians.index[mask].to_numpy()
    return(pareto.tolist())

# https://stackoverflow.com/questions/65107289/minimum-distance-between-two-axis-aligned-boxes-in-n-dimensions
def boxes_distance(A_min, A_max, B_min, B_max):
    delta1 = A_min - B_max
    delta2 = B_min - A_max
    u = np.max(np.array([np.zeros(len(delta1)), delta1]), axis=0)
    v = np.max(np.array([np.zeros(len(delta2)), delta2]), axis=0)
    dist = np.linalg.norm(np.concatenate([u, v]))
    return dist

def find_all_points_close(medians, pareto, x, dx, nudge=1.0):
    pareto_ext = []
    for bA in pareto:
        A_min = medians.loc[bA][x].to_numpy() - nudge*medians.loc[bA][dx].to_numpy()
        A_max = medians.loc[bA][x].to_numpy() + nudge*medians.loc[bA][dx].to_numpy()

        dists_AB = {}
        for bB in medians.index:
            B_min = medians.loc[bB][x].to_numpy() - nudge*medians.loc[bB][dx].to_numpy()
            B_max = medians.loc[bB][x].to_numpy() + nudge*medians.loc[bB][dx].to_numpy()
            dAB = boxes_distance(A_min, A_max, B_min, B_max)
            if dAB < 1e-1:
                pareto_ext.append(bB) 
    return np.unique(pareto_ext).tolist()

def plot_boxplots_df_df_ex(df, scores, df_ex, extrinsics):
    """    
    Plot ordered boxplots of scores and extrinsiscs
    NB: to filter builds  df_sel = df[df["nb_build"].isin(pareto)]
                          df_ex_sel = df_ex[df_ex["nb_build"].isin(pareto)]
    """
    medians = calc_medians_df_df_ex(df, scores, df_ex, extrinsics)
    nb = len(scores)+len(extrinsics)
    fig, ax = plt.subplots(1, nb, figsize=(nb*7.5, 5))
    i = 0
    for s in scores:
        if nb==1:
            axi = ax
        else:
            axi = ax[i]
        boxplot_sorted(df, by="nb_build", column=s, ax=axi)
        axi.axhline(medians.loc["official"][s],  c='grey', lw=3)
        axi.set_title(s)
        i = i+1
    for e in extrinsics:
        if nb==1:
            axi = ax
        else:
            axi = ax[i]
        boxplot_sorted(df_ex, by="nb_build", column="Extr-Remark", ax=axi, ascending=False)
        axi.axhline(medians.loc["official"][e],  c='grey', lw=3)
        axi.set_title(e)
        i = i+1
    return fig