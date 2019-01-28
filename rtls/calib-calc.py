#!/usr/bin/python3

import sys
import math
import random
import argparse
import tail

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot

from numpy import dot,diag


DEBUG = 0
VERBOSE = 0

CLOCK_GHZ = 63.8976
CLOCK_HZ  = CLOCK_GHZ * 1E9

Cvac = 299792458

DEVMAP = {
    'magpi1'  :  0,
    'magpi2'  :  1,
    'magpi3'  :  2,
    'magpi4'  :  3,
    'magpi5'  :  4,
    'magpi6'  :  5,
    'magpi7'  :  6,
    'magpi8'  :  7,
}


def estimate_antd(ndev,dist,dstd,derr,bidir=False,weighted=True):

    if bidir:
        L = int((ndev-1)*ndev)
    else:
        L = int((ndev-1)*(ndev/2))
        
    A = np.zeros((L,ndev))
    G = np.zeros((L))
    C = np.zeros((L))
    
    k = 0

    for i in range(ndev):
        for j in range(ndev):
            if bidir:
                if i != j:
                    A[k,i] = 1
                    A[k,j] = 1
                    G[k] = dstd[i,j]
                    C[k] = derr[i,j]
                    k += 1
            else:
                if i < j:
                    A[k,i] = 1
                    A[k,j] = 1
                    G[k] = dstd[i,j]
                    C[k] = derr[i,j]
                    k += 1
    
    if weighted:
        GG = diag(1/G)
        AA = dot(GG,A)
        CC = dot(C,GG)
    else:
        AA = A
        CC = C
        
    AX = lin.lstsq(AA,CC,rcond=None)
    CR = (AX[0]/Cvac) * CLOCK_HZ

    return CR


def main():
    
    global VERBOSE, DEBUG

    parser = argparse.ArgumentParser(description="TWR ANTD tool")

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-L', '--distance', type=float, default=10.0)
    parser.add_argument('-N', '--hosts', type=int, default=0)
    parser.add_argument('-f', '--file', type=str, default=None)
    parser.add_argument('-B', '--bidir', action='store_true', default=False)
    parser.add_argument('-W', '--weighted', action='store_true', default=False)

    args = parser.parse_args()

    VERBOSE = args.verbose

    Ndev = args.hosts

    dist = np.zeros((Ndev,Ndev))
    dstd = np.zeros((Ndev,Ndev))
    derr = np.zeros((Ndev,Ndev))
    
    with open(args.file, 'r') as ff:
        for line in ff:
            try:
                TOK = line.rstrip().split(',')

                i = DEVMAP[TOK[0]]
                j = DEVMAP[TOK[1]]

                dist[i,j] = float(TOK[2])
                dstd[i,j] = float(TOK[3])
                derr[i,j] = float(TOK[2]) - args.distance

                if not args.bidir:
                    dist[j,i] = dist[i,j]
                    dstd[j,i] = dstd[i,j]
                    derr[j,i] = derr[i,j]
                    
            except KeyError as err:
                print('Shit happened: {}'.format(err))

    print(dist)

    ANTD = estimate_antd(Ndev,dist,dstd,derr, bidir=args.bidir, weighted=args.weighted)

    for a in range(Ndev):
        msg1 = '#{}:'.format(a)
        msg2 = '0x{:04X}'.format( int(round(ANTD[a])) + 0x4000 )
        msg3 = '{:+d}'.format( int(round(ANTD[a])) )
        msg4 = '[{:+.3f}]'.format( ANTD[a] )
        msgs = '{:4s} {:8s} {:6s} {:s}'.format(msg1,msg2,msg3,msg4)
        print(msgs)

    

if __name__ == "__main__":
    main()

