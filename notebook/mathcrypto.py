# Copyright 2022 https://www.math-crypto.com
# GNU General Public License

import math
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib 

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