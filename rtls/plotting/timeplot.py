#!/usr/bin/python3
#

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


def running_mean(x,n):
    cc = np.cumsum(np.insert(x,0,0)) 
    return (cc[N:]-cc[:-n])/n


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-B', '--binsize', type=float, default=0.02)
    
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
            data.append([ int(row[3]), float(row[6]) ])


    ##
    ## Analysis
    ##

    D = np.array(data)
    T = D[:,0] / DW1000_CLOCK_HZ * 1000

    Tavg = np.mean(T)
    Tstd = np.std(T)
    
    Hbin = args.binsize   # [ms]
    Hmin = np.percentile(T,0.1)
    Hmax = np.percentile(T,99.9)
    Hrng = Hmax - Hmin
    Hcnt = int(2*Hrng/Hbin) + 1

    print(Tavg)
    print(Tstd)
    print(Hcnt)

    bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
    (hist,edges) = np.histogram(T,bins=bins)

    fig,ax = plot.subplots(figsize=(15,10),dpi=80)
    ax.set_title('Delay distribution')
    ax.set_xlabel('Delay [ms]')
    ax.set_ylabel('Samples')
    ax.text(0.90, 0.95, r'$\mu$={:.3f}ms'.format(Tavg), transform=ax.transAxes, size='x-large')
    ax.text(0.90, 0.90, r'$\sigma$={:.3f}ms'.format(Tstd), transform=ax.transAxes, size='x-large')
    ax.grid(True)
    ax.hist(T,bins)
    fig.tight_layout()
    plot.show()
    

        
if __name__ == "__main__": main()

