#!/usr/bin/python3
#

import argparse
import pprint
import math
import tail
import sys
import csv

import numpy as np
import matplotlib.pyplot as plt

from pprint import pprint


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
    parser.add_argument('-L', '--lin', action='store_true', default=False)
    
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
            data.append(row)


    ##
    ## Analysis
    ##

    D = np.array(data)

    fig,axs = plt.subplots(3,3)

    X = D[:,2]
    Y = D[:,9]
    axs[0,0].scatter(X,Y,s=0.5)
    axs[0,0].set_xlabel('Time')
    axs[0,0].set_ylabel('Distance')
    
    X = D[:,2]
    Y = D[:,10]
    axs[0,1].scatter(X,Y,s=0.5)
    axs[0,1].set_xlabel('Time')
    axs[0,1].set_ylabel('Clock Drift')

    X = D[:,2]
    Y = D[:,13]
    axs[0,2].scatter(X,Y,s=0.5)
    axs[0,2].set_xlabel('Time')
    axs[0,2].set_ylabel('Noise')
    
    X = D[:,11]
    Y = D[:,9]
    axs[1,0].scatter(X,Y,s=0.5)
    axs[1,0].set_xlabel('Rx Power')
    axs[1,0].set_ylabel('Distance')

    X = D[:,12]
    Y = D[:,9]
    axs[1,1].scatter(X,Y,s=0.5)
    axs[1,1].set_xlabel('FP Power')
    axs[1,1].set_ylabel('Distance')
    
    X = D[:,11]
    Y = D[:,13]
    axs[1,2].scatter(X,Y,s=0.5)
    axs[1,2].set_xlabel('Rx Power')
    axs[1,2].set_ylabel('Noise')
    
    X = np.array(D[:,6],np.double) + np.array(D[:,7],np.double)
    Y = D[:,9]
    axs[2,0].scatter(X,Y,s=0.5)
    axs[2,0].set_xlabel('Tx Power')
    axs[2,0].set_ylabel('Distance')

    Y = D[:,11]
    axs[2,1].scatter(X,Y,s=0.5)
    axs[2,1].set_xlabel('Tx Power')
    axs[2,1].set_ylabel('Rx Power')
    
    Y = D[:,13]
    axs[2,2].scatter(X,Y,s=0.5)
    axs[2,2].set_xlabel('Tx Power')
    axs[2,2].set_ylabel('Noise')
    
    plt.title('TWR Data')
    plt.show()
        

        
if __name__ == "__main__":
    main()

