#!/usr/bin/python3

import argparse
import math
import tail
import sys
import csv

import numpy as np
import matplotlib.pyplot as plot

from config import *


VERBOSE = 0
DEBUG = 0


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-T', '--title', type=str, default='')
    parser.add_argument('-B', '--binsize', type=float, default=0.1)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    
    ##
    ## Read data file
    ##
    
    data = []

    if args.file is None:
        args.file = '/dev/stdin'
    
    with open(args.file) as csvfile:
        CSV = csv.reader(csvfile, delimiter=',')
        for row in CSV:
            data.append([ float(row[6]), ])


    ##
    ## Analysis
    ##

    D = np.array(data)
    P = D[:,0]

    Pavg = np.mean(P)
    Pstd = np.std(P)
    
    Hmin = -85.0  #np.percentile(P,1.0)
    Hmax = -75.0  #np.percentile(P,99.0)
    Hrng = Hmax - Hmin

    if args.binsize is not None:
        Hcnt = int(Hrng/args.binsize) + 1
    else:
        Hcnt = 21

    print(Pavg)
    print(Pstd)
    print(Hcnt)

    bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
    (hist,edges) = np.histogram(P,bins=bins)

    fig,ax = plot.subplots(figsize=(15,10),dpi=80)
    ax.set_title(args.title)
    ax.set_xlabel('Power')
    ax.set_ylabel('Samples')
    ax.text(0.90, 0.95, r'$\mu$={:.3f}'.format(Pavg), transform=ax.transAxes, size='x-large')
    ax.text(0.90, 0.90, r'$\sigma$={:.3f}'.format(Pstd), transform=ax.transAxes, size='x-large')
    ax.grid(True)
    ax.hist(P,bins)
    fig.tight_layout()
    plot.show()
    
    
    
if __name__ == "__main__": main()

