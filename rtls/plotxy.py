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


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-c', '--columns', type=str, default=None)
    parser.add_argument('-X', '--xlim', type=str, default=None)
    parser.add_argument('-Y', '--ylim', type=str, default=None)
    parser.add_argument('-L', '--lin', action='store_true', default=False)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    if args.columns is not None:
        cols = [ int(col) for col in args.columns.split(',') ]
    else:
        cols = [ 0, 1 ]

    print('Using colums {}'.format(cols))

    if args.xlim is not None:
        vals = args.xlim[1:-1]
        xlims = vals.split(',')
        xlimA = float(xlims[0])
        xlimB = float(xlims[1])
    else:
        xlimA = -1E12
        xlimB =  1E12
        
    if args.ylim is not None:
        vals = args.ylim[1:-1]
        ylims = vals.split(',')
        ylimA = float(ylims[0])
        ylimB = float(ylims[1])
    else:
        ylimA = -1E12
        ylimB =  1E12

    
    ##
    ## Read data file
    ##
    
    data = []

    if args.file is None:
        args.file = '/dev/stdin'
    
    with open(args.file) as csvfile:
        CSV = csv.reader(csvfile, delimiter=',')
        for row in CSV:
            data.append( [ float(row[i]) for i in cols ] )


    ##
    ## Analysis
    ##

    D = np.array(data)
    Ix = (D[:,0]>xlimA) & (D[:,0]<xlimB)
    Iy = (D[:,1]>ylimA) & (D[:,1]<ylimB)

    X = D[Ix&Iy,0]
    Y = D[Ix&Iy,1]

    plt.scatter(X,Y)
    
    if args.lin:
        C = np.polyfit(X,Y,1)
        P = np.poly1d(C)
        print('Polyfit: {:.6f}'.format(C[0]))
        Xmin = min(X)
        Xmax = max(X)
        XX = np.linspace(Xmin,Xmax,100)
        YY = P(XX)
        plt.plot(XX,YY,'r')
        
    plt.title('Columns [{}]'.format(args.columns))
    plt.show()
        

        
if __name__ == "__main__":
    main()

