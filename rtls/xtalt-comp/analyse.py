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
    parser.add_argument('-M', '--match', action='store_true', default=False)
    parser.add_argument('-N', '--normalise', action='store_true', default=False)
    
    parser.add_argument('file', type=str, nargs='?', default=None, help="Data file")
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    if args.columns is not None:
        cols = [ int(col) for col in args.columns.split(',') ]
    else:
        cols = [ 0,1, ]

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

    plt.scatter(D[:,0],D[:,1])

    DATA = { }
    
    for (x,y) in D:
        if -20 < x < 100:
            key = '{:.2f}'.format(x)
            if key not in DATA:
                DATA[key] = {'sum':0.0,'cnt':0 }
            DATA[key]['sum'] += y
            DATA[key]['cnt'] += 1

    L = len(DATA)
    print('Data length is {} samples\n'.format(L))

    X = np.zeros(L)
    Y = np.zeros(L)
    C = 0.0
    n = 0
    for i in DATA:
        X[n] = i
        Y[n] = DATA[i]['sum'] / DATA[i]['cnt']
        if 40.0 < X[n] < 40.2:
            C = Y[n]
        n += 1
    
    if args.normalise:
        Y -= C
    
    plt.scatter(X,Y)

    X3 = np.zeros((L,4))
    I3 = np.zeros((L,4))
    
    for n in range(L):
        x = X[n] / 100
        i = ((X[n] - 23) * 1.14) / 256
        X3[n][3] = 1
        X3[n][2] = x
        X3[n][1] = x*x
        X3[n][0] = x*x*x
        I3[n][3] = 1
        I3[n][2] = i
        I3[n][1] = i*i
        I3[n][0] = i*i*i

    Cf = lin.lstsq(X3,Y,rcond=None)
    Ca = lin.lstsq(I3,Y,rcond=None)
    
    Ff = Cf[0]
    Fa = Ca[0]

    Xt = np.linspace(-40,100,5000)
    Xf = Xt / 100
    
    Yf = np.polyval(Ff,Xf)

    Xi = np.floor((Xt - 23) * 1.14)
    Fr = np.floor(Fa * 16)

    # Y = F0
    Yj = Fa[0]
    Yi = Fr[0]

    # Y = (Y * X) >> 8 + F1
    Yj = Yj * Xi / 256 + Fa[1]
    Yi = np.floor(Yi * Xi / 256) + Fr[1]

    # Y = (Y * X) >> 8 + F2
    Yj = Yj * Xi / 256 + Fa[2]
    Yi = np.floor(Yi * Xi / 256) + Fr[2]

    # Y = (Y * X) >> 8 + F3
    Yj = Yj * Xi / 256 + Fa[3]
    Yi = np.floor(Yi * Xi / 256) + Fr[3]

    # Y has 4 fractional bits
    Yi = Yi / 16

    if args.match:
        plt.plot(Xt,Yf,'c-')
        plt.plot(Xt,Yi,'g-')
        plt.plot(Xt,Yj,'b-')

    print('x = t / 100')
    print('PPM = {0[0]:.3f} x^3 + {0[1]:.3f} x^2 + {0[2]:.3f} x + {0[3]:.3f}'.format(Ff))
    print()

    print('x = ADCt - CALt')
    print('y = {:.0f}'.format(np.floor(Fr[0])))
    print('y = (y * x)>>8 + {:.0f}'.format(Fr[1]))
    print('y = (y * x)>>8 + {:.0f}'.format(Fr[2]))
    print('y = (y * x)>>8 + {:.0f}'.format(Fr[3]))
    print('PPM = y >> 4')
    print()

    plt.show()
    

if __name__ == "__main__":
    main()

