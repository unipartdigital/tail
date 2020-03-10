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
import matplotlib.pyplot as plt


class cfg():

    tx = '70b3d5b1e0000024'
    rx = '70b3d5b1e0000026'

    window     = 1.0
    tolerance  = 0.05
    

def rec2str(rec):
    ret  = '{:.9f}'.format(rec[0])
    ret += ',{.3f}'.format(rec[1])
    ret += ',{.2f}'.format(rec[2])
    ret += ',{.2f}'.format(rec[3])
    ret += '\n'
    return ret


def main():

    parser = argparse.ArgumentParser(description="Clock speed analyser")
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-P', '--plot', action='store_true', default=False)
    parser.add_argument('-W', '--window', type=float, default=cfg.window)
    parser.add_argument('-L', '--tolerance', type=float, default=cfg.tolerance)
    parser.add_argument('-T', '--tx', type=str, default=cfg.tx)
    parser.add_argument('-R', '--rx', type=str, default=cfg.rx)
    parser.add_argument('-o', '--output', type=str, default=None)
    parser.add_argument('file', type=str, default='/dev/stdin')
    
    args = parser.parse_args()

    window = int(args.window * 1E9)
    minwin = int(args.window * (1.00-args.tolerance) * 1E9)
    maxwin = int(args.window * (1.00+args.tolerance) * 1E9)
    
    tx = args.tx
    rx = args.rx

    EUIs = ((tx,rx), )

    blinks = BlinkStorm()
    blinks.load(args.file, EUIs)

    PPM = []
    
    id = blinks.minid
    while id < blinks.maxid:
        try:
            id1 = blinks.linsearch_fwd(id, EUIs)
            bl1 = blinks.get(id1)
            tx1 = bl1.getTx(tx)
            rx1 = bl1.getRx(rx)
            
            id = id1 + 1

            id2 = blinks.search(bl1.time + window, EUIs)
            bl2 = blinks.get(id2)
            tx2 = bl2.getTx(tx)
            rx2 = bl2.getRx(rx)

            delta = bl2.time - bl1.time
            if delta < minwin or delta > maxwin:
                continue

            dx = rx2.time_hires - rx1.time_hires
            dy = tx2.time_hires - tx1.time_hires

            if dx == 0 or dy == 0:
                continue
            
            ppm = (dx - dy) / dy * 1E6

            tx_temp = (tx1.temp + tx2.temp) / 2
            rx_temp = (rx1.temp + rx2.temp) / 2
            
            if -50 < ppm < 50:
                rec = (bl1.time*1E-9,ppm,tx_temp,rx_temp)
                PPM.append(rec)
                

        except (KeyError,ValueError,AttributeError):
            break
                    
        except KeyboardInterrupt:
            raise SystemExit


    if args.output:
        with open(args.output, 'w') as out:
            for rec in PPM:
                out.write(rec2str(rec))
    
    if args.plot:
        D = np.array(PPM)
        plt.plot(D[:,0], D[:,1], c='g')
        plt.show()
    
        
if __name__ == "__main__": main()

