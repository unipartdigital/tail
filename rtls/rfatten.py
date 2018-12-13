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


class Config():

    Ch     = 7
    Dist   = 5.34
    Power  = -75


CFG = Config()

VERBOSE = 0

PI = math.pi
CS = 299792458
CC = 4*PI/CS

FC = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )


def DAI(m,fc,pt):
    return pt - 20*np.log10(m*CC*fc*1e6)

def ADI(dBm,fc,pt):
    return 10**((pt-dBm)/20)/(CC*fc*1e6)


def CalcAtten(ch,dist,dBm):
    return dBm - DAI(dist,FC[ch],0)


def Plot(Ch=7, Pt=0.0, Range=None):

    if Range is None:
        Range = ( 1, 100 )

    X = np.linspace(Range[0],Range[1],100)
    Y = DAI(X,FC[Ch],Pt)
    
    YY = np.linspace(np.min(Y),np.max(Y),100)
    XX = ADI(YY,FC[Ch],Pt)
    
    
    fig,ax = plot.subplots(1,2,figsize=(20,10),dpi=120)
    
    ax[0].set_title('Ch{} Pt:{:.1f}dBm'.format(Ch,Pt))
    ax[0].set_ylabel('[dBm]')
    ax[0].set_xlabel('[m]')
    ax[0].grid(True)
    
    ax[0].plot(X,Y,'-')
    ax[0].plot(XX,YY,'-')
    
    
    Y1 = DAI(X,FC[1],Pt)
    Y2 = DAI(X,FC[2],Pt)
    Y3 = DAI(X,FC[3],Pt)
    Y4 = DAI(X,FC[4],Pt)
    Y5 = DAI(X,FC[5],Pt)
    Y7 = DAI(X,FC[7],Pt)
    
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
    parser.add_argument('-c', '--channel', type=int, default=CFG.Ch, help='channel')
    parser.add_argument('-d', '--distance', type=float, default=CFG.Dist, help='distance')
    parser.add_argument('-P', '--power', type=float, default=CFG.Power, help='power')
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    Dist  = args.distance
    Pwr   = args.power
    Ch    = args.channel

    Pt    = CalcAtten(Ch,Dist,Pwr)

    if DAI(Dist,FC[Ch],Pt) != Pwr:
        raise ValueError
    

    print('Channel   : {}'.format(Ch))
    print('Distance  : {:.3f}m'.format(Dist))
    print('Power     : {:.1f}dBm'.format(Pwr))
    print('Atten     : {:.1f}dBm'.format(Pt))

    Plot(Ch,Pt)


if __name__ == "__main__":
    main()


