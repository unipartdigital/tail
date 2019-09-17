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


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-c', '--columns', type=str, default=None)
    parser.add_argument('-X', '--xlim', type=str, default='-')
    parser.add_argument('-Y', '--ylim', type=str, default='-')
    parser.add_argument('-L', '--lin', action='store_true', default=False)
    
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
        cols.append(0)
        lims.append((-1E99,1E99))
        cols.append(1)
        lims.append((-1E99,1E99))

    print('Using colums {}'.format(cols))

    
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
    Y = D[:,1]

    AVG = np.mean(Y)
    STD = np.std(Y)

    XLEN = len(X)
    XSUP = (min(X), max(X))
    YSUP = (min(Y), max(Y))

    plt.scatter(X,Y)

    if args.lin:
        C = np.polyfit(X,Y,1)
        P = np.poly1d(C)
        print('Polyfit: {:.6f} {:.6f}'.format(C[0],C[1]))
        Xmin = min(X)
        Xmax = max(X)
        XX = np.linspace(Xmin,Xmax,100)
        YY = P(XX)
        plt.plot(XX,YY,'r')
        
    plt.title('Columns [{}]'.format(args.columns))
    plt.show()
        

        
if __name__ == "__main__":
    main()

