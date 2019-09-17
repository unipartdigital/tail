#!/usr/bin/python3
#
# Calcalate reference anchor ANTDs from the data collected by ref-antd-collect.
#
# Usage: ref-antd-calc <-f|--file> <-L|--distance> <-B|--bidir> <-W|--weighted>
#
#  distance		Distance used in collection
#  bidir		Use host1:host2 measurement also for host2:host1
#  weighted		Weight the calculation with distance variance
#

import sys
import math
import random
import argparse
import tail

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot

from numpy import dot,diag

from tail import prints


VERBOSE = 0

CLOCK_GHZ = 63.8976
CLOCK_HZ  = CLOCK_GHZ * 1E9

Cvac = 299792458

DEVMAP = {
    'magpi0'  :  0,
    'magpi1'  :  1,
    'magpi2'  :  2,
    'magpi3'  :  3,
    'magpi4'  :  4,
    'magpi5'  :  5,
    'magpi6'  :  6,
    'magpi7'  :  7,
    'magpi8'  :  8,
}


def hostname(id):
    for host in DEVMAP:
        if DEVMAP[host] == id:
            return host
    return None


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

    return (AX[0],CR)


def main():
    
    global VERBOSE

    parser = argparse.ArgumentParser(description="TWR ANTD tool")

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-L', '--distance', type=float, default=10.0)
    parser.add_argument('-f', '--file', type=str, default=None)
    parser.add_argument('-B', '--bidir', action='store_true', default=False)
    parser.add_argument('-W', '--weighted', action='store_true', default=False)

    args = parser.parse_args()

    VERBOSE = args.verbose

    Ndev = len(DEVMAP)

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

    (CORR,ANTD) = estimate_antd(Ndev,dist,dstd,derr, bidir=args.bidir, weighted=args.weighted)

    print('\nCorrection:')
        
    for a in range(Ndev):
        msg1 = '  {}:'.format(hostname(a))
        msg2 = '{:+d}'.format( int(round(ANTD[a])) )
        msg3 = '[{:+.3f}]'.format( ANTD[a] )
        msgs = '{:4s} {:4s} {:s}'.format(msg1,msg2,msg3)
        print(msgs)


    print('\nEstimated errors:')
        
    for a in range(Ndev):
        for b in range(Ndev):
            if a != b:
                err = derr[a,b] - CORR[a] - CORR[b]
                msg = '{:+.3f}m'.format(err)
            else:
                msg = '-'
            prints('  {:8s}'.format(msg))
        print()
            

if __name__ == "__main__":
    main()

