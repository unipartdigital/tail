#!/usr/bin/python3
#

import argparse
import pprint
import math
import sys
import csv

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plt

from numpy import dot,diag

from pprint import pprint


VERBOSE = 0


def main():

    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="Plotter")

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-c', '--columns', type=str, default=None)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    if args.columns is not None:
        cols = [ int(col) for col in args.columns.split(',') ]
    else:
        cols = [ 4, 2 ]

    
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

    DATA = { }
    
    for (x,y) in D:
        key = '{:.2f}'.format(x)
        if key not in DATA:
            DATA[key] = {'sum':0.0,'cnt':0 }
        DATA[key]['sum'] += y
        DATA[key]['cnt'] += 1

    C = 0.0
    for i in DATA:
        X = float(i)
        Y = DATA[i]['sum'] / DATA[i]['cnt']
        if 40.0 < X < 40.2:
            C = Y

    for (x,y) in D:
        msg = '{:.2f},{:.3f}'.format(x,y-C)
        print(msg)
    

if __name__ == "__main__":
    main()

