#!/usr/bin/python3

import sys
import time
import math
import json
import argparse
import pprint
import csv

from buster import *

import numpy as np
import matplotlib.pyplot as plot



def main():

    parser = argparse.ArgumentParser(description="Clock speed analyser")
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-T', '--tx', type=str, default=None)
    parser.add_argument('-R', '--rx', type=str, default=None)
    parser.add_argument('-b', '--bins', type=int, default=None)
    parser.add_argument('-B', '--binsize', type=float, default=None)
    parser.add_argument('-P', '--percentile', type=float, default=None)
    parser.add_argument('-d', '--distance', type=float, default=0.0)
    parser.add_argument('file', type=str, default='/dev/stdin')
    
    args = parser.parse_args()

    dist = args.distance

    dmin = dist - 1.0
    dmax = dist + 1.0
    
    tx = args.tx
    rx = args.rx

    A2B = ((tx,rx),)
    B2A = ((rx,tx),)
    EUIs = ((tx,rx),(rx,tx),)

    blinks = BlinkStorm()
    blinks.load(args.file, EUIs)

    data = []

    index = 1
    id = blinks.minid
    while id < blinks.maxid:
        try:
            id1 = blinks.linsearch_fwd(id, A2B)
            bl1 = blinks.get(id1)
            tx1 = bl1.get(tx)
            rx1 = bl1.get(rx)

            id2 = blinks.linsearch_fwd(id1, B2A)
            bl2 = blinks.get(id2)
            tx2 = bl2.get(rx)
            rx2 = bl2.get(tx)

            id3 = blinks.linsearch_fwd(id2, A2B)
            bl3 = blinks.get(id3)
            tx3 = bl3.get(tx)
            rx3 = bl3.get(rx)

            id = id3
            
            T1 = tx1.time_raw
            T2 = rx1.time_raw
            T3 = tx2.time_raw
            T4 = rx2.time_raw
            T5 = tx3.time_raw
            T6 = rx3.time_raw

            T41 = T4 - T1
            T32 = T3 - T2
            T54 = T5 - T4
            T63 = T6 - T3
            T51 = T5 - T1
            T62 = T6 - T2
            
            Tof = (T41*T63 - T32*T54) / (T51+T62)
            Dof = (Tof / DW1000_CLOCK_HZ) * Cabs
            
            PPM = (T62 - T51) / T51 * 1E6

            Time = rx1.time

            #print('{}: @{} {} {:.3f}m {:.3f}ppm'.format(index,id1,Time,Dof,PPM))

            if dmin < Dof < dmax:
                data.append((index,Time,Dof,PPM))
                index += 1

        except (KeyError,AttributeError,ValueError):
            break
                    
        except KeyboardInterrupt:
            raise SystemExit

    D = np.array(data)
    Y = D[:,0]
    X = D[:,2]
    C = len(X)

    Xavg = np.mean(X)
    Xstd = np.std(X)

    if args.percentile is not None:
        Hmin = np.percentile(X, 100-args.percentile)
        Hmax = np.percentile(X, args.percentile)
    else:
        Hmin = np.min(X)
        Hmax = np.max(X)
    
    Hrng = Hmax - Hmin

    if args.bins is not None:
        Hcnt = args.bins
    elif args.binsize is not None:
        Hcnt = int(Hrng/args.binsize) + 1
    else:
        Hcnt = 64

    bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
    (hist,edges) = np.histogram(X,bins=bins)

    fig,ax = plot.subplots(2,figsize=(15,20),dpi=80)

    ax1 = ax[0]
    ax2 = ax[1]
    
    #ax1.set_title(args.title)
    ax1.text(0.90, 0.95, r'$\mu$={:.3f}'.format(Xavg), transform=ax1.transAxes, size='x-large')
    ax1.text(0.90, 0.90, r'$\sigma$={:.3f}'.format(Xstd), transform=ax1.transAxes, size='x-large')
    ax1.text(0.90, 0.85, r'N={:d}'.format(C), transform=ax1.transAxes, size='x-large')
    ax1.grid(True)
    ax1.hist(X,bins)

    ax2.plot(Y,X)
    
    fig.tight_layout()
    plot.show()
    
        
if __name__ == "__main__": main()

