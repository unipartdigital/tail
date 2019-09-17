#!/usr/bin/python3

import argparse
import math
import tail
import sys
import csv

import numpy as np
import matplotlib.pyplot as plot

from pprint import pprint


VERBOSE = 0


def main():

    global VERBOSE
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-c', '--columns', type=str, default=None)
    parser.add_argument('-T', '--title', type=str, default='')
    parser.add_argument('-b', '--bins', type=int, default=None)
    parser.add_argument('-B', '--binsize', type=float, default=None)
    parser.add_argument('-P', '--percentile', type=float, default=None)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    cols = []
    lims = []
    
    if args.columns is not None:
        for col in args.columns.split(','):
            if ':' in col:
                (c,a,b) = col.split(':')
                cols.append(int(c))
                lims.append((float(a),float(b)))
            else:
                cols.append(int(col))
                lims.append((-1E99,1E99))

    else:
        cols.append(1)
        lims.append((-1E99,1E99))


    print(cols)
    print(lims)
    
        
    ##
    ## Read data file
    ##
    
    data = []

    if args.file is None:
        args.file = '/dev/stdin'
    
    with open(args.file) as csvfile:
        CSV = csv.reader(csvfile, delimiter=',')
        for row in CSV:
            if all([ lims[i][0]<=float(row[c])<=lims[i][1] for i,c in enumerate(cols) ]):
                data.append([ float(row[i]) for i in cols ])

    ##
    ## Analysis
    ##

    D = np.array(data)
    X = D[:,0]
    C = len(D)

    Xavg = np.mean(X)
    Xstd = np.std(X)

    if args.percentile is not None:
        Hmin = np.percentile(X, 100-args.percentile)
        Hmax = np.percentile(X, args.percentile)
    else:
        Hmin = np.min(X)
        Hmax = np.max(X)
    
    Hrng = Hmax - Hmin

    if args.bins is not None:
        Hcnt = args.bins
    elif args.binsize is not None:
        Hcnt = int(Hrng/args.binsize) + 1
    else:
        Hcnt = 100

    bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
    (hist,edges) = np.histogram(X,bins=bins)

    fig,ax = plot.subplots(figsize=(15,10),dpi=80)
    
    ax.set_title(args.title)
    ax.text(0.90, 0.95, r'$\mu$={:.3f}'.format(Xavg), transform=ax.transAxes, size='x-large')
    ax.text(0.90, 0.90, r'$\sigma$={:.3f}'.format(Xstd), transform=ax.transAxes, size='x-large')
    ax.text(0.90, 0.85, r'N={:d}'.format(C), transform=ax.transAxes, size='x-large')
    ax.grid(True)
    ax.hist(X,bins)
    
    fig.tight_layout()
    plot.show()
    
    
    
if __name__ == "__main__": main()

