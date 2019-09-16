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


DW1000_CLOCK_GHZ = 63.8976
DW1000_CLOCK_HZ  = DW1000_CLOCK_GHZ * 1E9

VERBOSE = 0


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-c', '--columns', type=str, default=None)
    parser.add_argument('-B', '--bins', type=int, default=None)
    parser.add_argument('-L', '--lin', action='store_true', default=False)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    if args.columns is not None:
        cols = [ int(col) for col in args.columns.split(',') ]
    else:
        cols = [ 25, ]

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
            data.append( [ float(row[i]) for i in cols ] )


    ##
    ## Analysis
    ##

    D = np.array(data)
    
    YY = D[0,0]

    Y = (D[:,0] - YY) / DW1000_CLOCK_HZ
    X = range(len(Y))

    print(Y)
    

    C = np.polyfit(X,Y,1)
    P = np.poly1d(C)
    print('Polyfit: {:.6f} {:.6f}'.format(C[0],C[1]))
    YY = P(X)

    YD = Y -YY

    plt.scatter(X,YD)

    plt.show()
        

        
if __name__ == "__main__":
    main()

