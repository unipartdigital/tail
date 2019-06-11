#!/usr/bin/python3

import sys
import math
import random
import argparse

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot

from numpy import dot,diag


DEBUG = 0
VERBOSE = 0

PPM_SIGMA   = 0.0
HWD_SIGMA   = 0.0
TOF_SIGMA   = 0.0
DIST_SIGMA  = 0.0
BLINK_SIGMA = 0.0

CLOCK_GHZ = 63.8976
CLOCK_HZ  = CLOCK_GHZ * 1E9

Cvac = 299792458
Cair = 299705000


DEVICE = {
    0: {
        'id'      :  0,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    1: {
        'id'      :  1,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    2: {
        'id'      :  2,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    3: {
        'id'      :  3,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    4: {
        'id'      :  4,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    5: {
        'id'      :  5,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    6: {
        'id'      :  6,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    7: {
        'id'      :  7,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
    8: {
        'id'      :  8,
        'ppm'     :  0.0,
        'hwd'     : [0,0],
        'antd'    : [0,0],
        'derr'    :  0.000,
        'clk'     :  0,
        'coord'   : (0,0,0),
    },
}


def randPPM(pid,sigma=0.0):
    DEVICE[pid]['ppm'] = random.normalvariate(0,sigma)

def resetClock(pid):
    DEVICE[pid]['clk'] = 0

def randClock(pid,bits=40):
    DEVICE[pid]['clk'] = int(random.getrandbits(bits))

def getClockHz(pid):
    Hz = CLOCK_HZ
    Hz += CLOCK_HZ*DEVICE[pid]['ppm']*1E-6
    return Hz

def getNorm(src,dst):
    Xd  = DEVICE[src]['coord'][0] - DEVICE[dst]['coord'][0]
    Yd  = DEVICE[src]['coord'][1] - DEVICE[dst]['coord'][1]
    Zd  = DEVICE[src]['coord'][2] - DEVICE[dst]['coord'][2]
    Ds  = math.sqrt(Xd*Xd + Yd*Yd + Zd*Zd)
    return Ds

def getDist(src,dst,sigma=0.0):
    Ds  = getNorm(src,dst)
    #Ds += DEVICE[src]['derr']
    #Ds += DEVICE[dst]['derr']
    Ds += random.normalvariate(0,sigma)
    return Ds

def getTof(src,dst,sigma=0.0):
    Tclk = getDist(src,dst,sigma) / Cvac
    return Tclk

def getTofTicks(src,dst,dsigma=0.0,tsigma=0.0):
    Jiff = getClockHz(dst) * getTof(src,dst,dsigma)
    Jiff += random.normalvariate(0,tsigma)
    return int(Jiff)

def randHWD(pid,sigma=0.0):
    D = random.normalvariate(0,sigma)
    DEVICE[pid]['hwd'][0] = int(D)
    DEVICE[pid]['hwd'][1] = int(D)

def getHWD(pid,dir):
    Jiff  = DEVICE[pid]['hwd'][dir]
    return int(Jiff)

def resetANTD(pid):
    DEVICE[pid]['antd'] = [0,0]

def setANTD(pid,dir,val):
    DEVICE[pid]['antd'][dir] = val

def getANTD(pid,dir):
    return DEVICE[pid]['antd'][dir]

def getTicks(pid,time):
    return int(DEVICE[pid]['clk']) + int(time*getClockHz(pid))

def getBlink(src,dst,time,dir):
    if dir == 0:
        return getTicks(src,time) + getANTD(src,0)
    else:
        return getTicks(dst,time) + getHWD(dst,0) + getTofTicks(src,dst,DIST_SIGMA,TOF_SIGMA) + getHWD(src,1) - getANTD(src,1)


def DECA_TWR(remote):

    SCL = CLOCK_GHZ

    r1 = remote[0]
    r2 = remote[1]

    randClock(r1)
    randClock(r2)

    E1 = random.normalvariate(10E-3, BLINK_SIGMA)
    E2 = random.normalvariate(20E-3, BLINK_SIGMA)
    E3 = random.normalvariate(30E-3, BLINK_SIGMA)

    T1 = getBlink(r1,r2,E1,0)
    T2 = getBlink(r1,r2,E1,1)
    T3 = getBlink(r2,r1,E2,0)
    T4 = getBlink(r2,r1,E2,1)
    T5 = getBlink(r1,r2,E3,0)
    T6 = getBlink(r1,r2,E3,1)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / SCL
    Lof = Dof * Cvac * 1E-9
        
    return (Lof,Dof)


def test_run(remote,args):
    
    delays = []
    
    try:
        for i in range(args.count):

            (Lof,Dof) = DECA_TWR(remote)

            delays.append(Dof)

            if VERBOSE > 1:
                msg  = ' ** '
                msg += 'Lof:{:.3f}m '.format(Lof)
                msg += 'ToF:{:.3f}ns '.format(Dof)
                print(msg)
            
    except KeyboardInterrupt:
        print('\nStopping...')

    cnt = len(delays)
        
    if cnt > 0:
        
        Davg = np.mean(delays)
        Dstd = np.std(delays)
        Dmed = np.median(delays)
        
        Lavg = Davg * Cvac * 1E-9
        Lstd = Dstd * Cvac * 1E-9
        Lmed = Dmed * Cvac * 1E-9
        
        print()
        print('FINAL STATISTICS:')
        print('  Samples:  {} [{:.1f}%]'.format(cnt,(100*cnt/args.count)-100))
        print('  Average:  {:.3f}m ={:.3f}ns'.format(Lavg,Davg))
        print('  Median:   {:.3f}m ={:.3f}ns'.format(Lmed,Dmed))
        print('  Std.Dev:  {:.3f}m ={:.3f}ns'.format(Lstd,Dstd))
        print()
    
        if args.hist or args.plot:
            
            Hbin = args.binsize
            if args.range > 0:
                Hrng = args.range
            else:
                Hrng = -2.0 * args.range * Dstd

            Hmin = Davg - Hrng/2
            Hmax = Davg + Hrng/2
            Hcnt = int(Hrng/Hbin) + 1
            bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
            (hist,edges) = np.histogram(delays,bins=bins)

            if args.hist:
                print()
                print('HISTOGRAM:')
                for i in range(len(hist)):
                    print('   {:.3f}: {:d}'.format(edges[i],hist[i]))

            if args.plot:
                fig,ax = plot.subplots(figsize=(15,10),dpi=80)
                ax.set_title('Delay distribution')
                ax.set_xlabel('Delay [ns]')
                ax.set_ylabel('Samples')
                ax.text(0.80, 0.85, r'$\mu$={:.3f}m'.format(Lavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.80, r'$\sigma$={:.3f}m'.format(Lstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.85, r'$\mu$={:.3f}ns'.format(Davg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.80, r'$\sigma$={:.3f}ns'.format(Dstd), transform=ax.transAxes, size='x-large')
                ax.grid(True)
                ax.hist(delays,bins)
                fig.tight_layout()
                plot.show()



def test_algo1(args):

    Ndev = 9
    
    dist = np.zeros((Ndev,Ndev))
    dstd = np.zeros((Ndev,Ndev))
    derr = np.zeros((Ndev,Ndev))
    
    try:
        for a in range(Ndev):
            for b in range(Ndev):
                if a == b:
                    dist[a,b] = 0.0
                    dstd[a,b] = 0.0
                    derr[a,b] = 0.0
                    continue
                
                DEVICE[a]['coord'] = ( 0,0,0)
                DEVICE[b]['coord'] = (10,0,0)

                values = []
                
                for i in range(args.count):
                    (Lof,Dof) = DECA_TWR((a,b))
                    values.append(Lof)

                Lavg = np.mean(values)
                Lstd = np.std(values)
                Lerr = Lavg - getNorm(a,b)

                dist[a,b] = Lavg
                dstd[a,b] = Lstd
                derr[a,b] = Lerr
                
    except KeyboardInterrupt:
        print('\nStopping...')

    L = int((Ndev-1)*(Ndev/2))

    A = np.zeros((L,Ndev))
    G = np.zeros((L))
    C = np.zeros((L))
    
    k = 0
    
    for i in range(Ndev):
        for j in range(i+1,Ndev):
            A[k,i] = 1
            A[k,j] = 1
            G[k] = dstd[i,j]
            C[k] = derr[i,j]
            k += 1
                
    if True:
        GG = diag(1/G)
        AA = dot(GG,A)
        CC = dot(C,GG)
    else:
        AA = A
        CC = C
        
    AX = lin.lstsq(AA,CC,rcond=None)
    AB = AX[0]
        
    ANTD = (AB/Cvac) * CLOCK_HZ

    for a in range(Ndev):
        msg1 = '#{}:'.format(a)
        msg2 = '[{0[0]:+d},{0[1]:+d}]'.format(DEVICE[a]['hwd'])
        msg3 = '{:+d}'.format(int(round(ANTD[a])))
        msg4 = '[{:+.3f}]'.format(ANTD[a])
        msgs = '{:4s} HWD:{:10s} ANTD:{:10s} {:s}'.format(msg1,msg2,msg3,msg4)
        print(msgs)
                

def main():
    
    global VERBOSE, DEBUG, TOF_SIGMA, HWD_SIGMA, DIST_SIGMA, BLINK_SIGMA

    RANGE = 1.0
    BINSIZE = 2 / CLOCK_GHZ
    
    parser = argparse.ArgumentParser(description="TWR delay tool")

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=1000, help='Number of blinks')
    parser.add_argument('-H', '--hist', action='store_true', default=False, help='Print histogram')
    parser.add_argument('-P', '--plot', action='store_true', default=False, help='Plot histogram')
    parser.add_argument('--range', type=float, default=RANGE)
    parser.add_argument('--binsize', type=float, default=BINSIZE)
    parser.add_argument('--ppm-sigma', type=float, default=PPM_SIGMA, help='Clock PPM sigma')
    parser.add_argument('--hwd-sigma', type=float, default=HWD_SIGMA, help='Hardware delay sigma [ticks]')
    parser.add_argument('--tof-sigma', type=float, default=TOF_SIGMA, help='Time-of-flight sigma [ticks]')
    parser.add_argument('--dist-sigma', type=float, default=DIST_SIGMA, help='Distance sigma [m]')
    parser.add_argument('--blink-sigma', type=float, default=BLINK_SIGMA, help='Blink time sigma [s]')
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    TOF_SIGMA = args.tof_sigma
    HWD_SIGMA = args.hwd_sigma
    DIST_SIGMA = args.dist_sigma
    BLINK_SIGMA = args.blink_sigma

    Ndev = 9

    for a in range(Ndev):
        resetANTD(a)
        randHWD(a,args.hwd_sigma)
        randPPM(a,args.ppm_sigma)
        msg1 = '#{}:'.format(a)
        msg2 = '({0[0]},{0[1]},{0[2]})'.format(DEVICE[a]['coord'])
        msg3 = '{:+.1f}ppm'.format(DEVICE[a]['ppm'])
        msg4 = 'HWD:[{0[0]:+d},{0[1]:+d}]'.format(DEVICE[a]['hwd'])
        msgs = '{:4s} {:10s} {:10s} {:10s}'.format(msg1,msg2,msg3,msg4)
        print(msgs)
        
    #test_run((0,4),args)
    test_algo1(args)
    

if __name__ == "__main__":
    main()

