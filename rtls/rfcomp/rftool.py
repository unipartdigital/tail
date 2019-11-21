#!/usr/bin/python3
#
# Standard propagation model for RF signals
#

import sys
import math
import argparse

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot


class cfg():

    channel    = 5
    rxlevel    = None
    txlevel    = -12.3
    distance   = 5.04


VERBOSE = 0

PI = math.pi
CS = 299792458
CC = 4*PI/CS

FC = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )


def Dist2Attn(m,MHz):
    return 20*np.log10(m*CC*MHz*1e6)

def Attn2Dist(dBm,MHz):
    return (10**(dBm/20))/(CC*MHz*1e6)

def CalcTxPower(ch,dist,rxlevel):
    return rxlevel + Dist2Attn(dist,FC[ch])

def CalcRxPower(ch,dist,txlevel):
    return txlevel - Dist2Attn(dist,FC[ch])

def CalcDist(ch, txlevel, rxlevel):
    return Attn2Dist(txlevel-rxlevel, FC[ch])


def Plot(Ch=5, Ptx=0.0, Range=None):

    if Range is None:
        Range = ( 1, 100 )

    X = np.linspace(Range[0],Range[1],100)
    Y = DAI(X,FC[Ch],Ptx)
    
    YY = np.linspace(np.min(Y),np.max(Y),100)
    XX = ADI(YY,FC[Ch],Ptx)
    
    
    fig,ax = plot.subplots(1,2,figsize=(20,10),dpi=120)
    
    ax[0].set_title('Ch{} TxPower:{:.1f}dBm'.format(Ch,Ptx))
    ax[0].set_ylabel('[dBm]')
    ax[0].set_xlabel('[m]')
    ax[0].grid(True)
    
    ax[0].plot(X,Y,'-')
    ax[0].plot(XX,YY,'-')
    
    
    Y1 = DAI(X,FC[1],Ptx)
    Y2 = DAI(X,FC[2],Ptx)
    Y3 = DAI(X,FC[3],Ptx)
    Y4 = DAI(X,FC[4],Ptx)
    Y5 = DAI(X,FC[5],Ptx)
    Y7 = DAI(X,FC[7],Ptx)
    
    ax[1].set_title('Channels')
    ax[1].set_ylabel('[dBm]')
    ax[1].set_xlabel('[m]')
    ax[1].grid(True)
    
    ax[1].plot(X,Y1,'-', label='Ch1')
    ax[1].plot(X,Y2,'-', label='Ch2')
    ax[1].plot(X,Y3,'-', label='Ch3')
    ax[1].plot(X,Y4,'-', label='Ch4')
    ax[1].plot(X,Y5,'-', label='Ch5')
    ax[1].plot(X,Y7,'-', label='Ch7')

    ax[1].legend(bbox_to_anchor=(1.05,1), loc=2)
    
    plot.show()



def main():
    
    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="RF propagation analysis")

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-c', '--channel', type=int, default=cfg.channel, help='channel')
    parser.add_argument('-d', '--distance', type=float, default=cfg.distance, help='calibration distance')
    parser.add_argument('-l', '--rxlevel', type=float, default=cfg.rxlevel, help='calibration rx level')
    parser.add_argument('-t', '--txlevel', type=float, default=cfg.txlevel, help='calibration tx level')
    parser.add_argument('-P', '--plot', action='store_true', default=False)
    
    parser.add_argument('points', type=float, nargs='*', help="distance points")

    args = parser.parse_args()

    VERBOSE = args.verbose

    Ch = args.channel

    cfg.distance  = args.distance

    if args.txlevel is not None:
        cfg.txlevel = args.txlevel
        cfg.rxlevel = CalcRxPower(Ch,  cfg.distance, cfg.txlevel)
    elif args.rxlevel is not None:
        cfg.rxlevel = args.rxlevel
        cfg.txlevel = CalcTxPower(Ch, cfg.distance, cfg.rxlevel)

    if Dist2Attn(cfg.distance, FC[Ch]) != cfg.txlevel - cfg.rxlevel:
        raise ValueError

    print('Channel   : {}'.format(Ch))
    print('Cal.Dist  : {:.3f}m'.format(cfg.distance))
    print('Cal.Level : {:.1f}dBm'.format(cfg.rxlevel))
    print('TxPower   : {:.1f}dBm'.format(cfg.txlevel))

    for val in args.points:
        if val > 0.0:
            rx_dist  = val
            rx_power = CalcRxPower(Ch, rx_dist, cfg.txlevel)
        else:
            rx_power = val
            rx_dist  = CalcDist(Ch, cfg.txlevel, val)
        print('Rx-level  : {:.1f}dBm @ {:.3f}m'.format(rx_power,rx_dist))

    if args.plot:
        Plot(Ch,cfg.txlevel)


if __name__ == "__main__":
    main()


