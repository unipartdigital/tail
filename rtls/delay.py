#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
#

import argparse
import socket
import pprint
import math
import tail

import numpy as np
import numpy.linalg as lin

from numpy import dot


class Config():

    blinks     = 100
    
    rpc_port   = 61666
    rpc_addr   = None

    dw1000_attrs = (
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
        'channel',
        'pcode',
        'txpsr',
        'prf',
        'rate',
        'antd',
        'xtalt',
        'smart_power',
    )


cfg = Config()


def findBlink(blks, anc1, anc2, start=None, search=100, skip=0):
    skipped = 0
    if start is not None:
        for i in range(start,start+search):
            if i in blks:
                if anc1 in blks[i] and anc2 in blks[i]:
                    if 'tss' in blks[i][anc1] and 'tss' in blks[i][anc2]:
                        if blks[i][anc1]['dir'] == 'TX' and blks[i][anc2]['dir'] == 'RX':
                            skipped += 1
                            if skipped > skip:
                                return i
    return None


def findFwdBwdPair(blks, anc1, anc2, start, search=100):
    fwdi = findBlink(blks, anc1, anc2, start, search)
    bwdi = findBlink(blks, anc2, anc1, fwdi, search)
    return (fwdi,bwdi)

def findFwdPair(blks, anc1, anc2, start, search=100, skip=0):
    fwd1 = findBlink(blks, anc1, anc2, start, search, 0)
    fwd2 = findBlink(blks, anc1, anc2, start, search, skip+1)
    return (fwd1,fwd2)


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    parser.add_argument('-D', '--dist', type=float, default=1)
    parser.add_argument('-W', '--window', type=int, default=8)
    parser.add_argument('-S', '--skip', type=int, default=0)
    parser.add_argument('-n', '--blinks', type=int, default=cfg.blinks)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remotes', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()
    
    Ds = args.dist / 299700000
    Dj = int(2*Ds*65536E9)<<16

    remotes = [ ]
    
    for remote in args.remotes:
        addr = socket.getaddrinfo(remote, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': remote, 'addr': addr, 'EUI': None } )

    rpc_addr = [ rem['addr'] for rem in remotes ]
    rpc_bind = ('', args.port)

    rpc = tail.RPC(rpc_bind)
    blk = tail.Blinker(rpc)

    for addr in rpc_addr:
        rpc.setAttr(addr, 'rate', 850)
        rpc.setAttr(addr, 'txpsr', 1024)
    
    for remote in remotes:
        addr = remote['addr']
        remote['EUI'] = rpc.getEUI(addr)
        print('DW1000 parameters @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(addr, attr)
            print('  {}={}'.format(attr, val))

    timer = tail.Timer()
    
    for i in range(args.blinks):
        for addr in rpc_addr:
            blk.Blink(addr)
            timer.nap(0.01)

    blk.stop()
    rpc.stop()

    
    ##
    ## Add analysis code here
    ##

    DdCNT = 0
    DdSUM = 0

    CrCNT = 0
    CrSUM = 0.0
    CrSQR = 0.0

    PaCNT = 0
    PaSUM = 0.0
    PaSQR = 0.0
    
    PbCNT = 0
    PbSUM = 0.0
    PbSQR = 0.0

    eui1 = remotes[0]['EUI']
    eui2 = remotes[1]['EUI']

    blks = blk.blinks

    mini = min(blks.keys())
    maxi = max(blks.keys())

    Pab = 1.000
    Cor = 0.000

    for i in range(mini,maxi-args.window):

        Ga = [ (1,1) ]
        Ha = [ (2)   ]
    
        if True:

            for j in range(args.window):
                
                (fwd,swd) = findFwdPair(blks, eui1, eui2, i+j, 100, args.skip)
                
                if swd is not None:

                    ##print('FWD @{} [{},{}]'.format(start,fwd,swd))
                    
                    J1 = blks[fwd][eui1]['tss']
                    J2 = blks[fwd][eui2]['tss']
                    J3 = blks[swd][eui1]['tss']
                    J4 = blks[swd][eui2]['tss']
                    
                    T31 = (J3 - J1) / 4294967296E9
                    T24 = (J2 - J4) / 4294967296E9
                    
                    Ga.append((T31,T24))
                    Ha.append((0))
                    
        if True:
            
            for j in range(args.window):
            
                (fwd,swd) = findFwdPair(blks, eui2, eui1, i+j, 100, args.skip)
                
                if swd is not None:

                    ##print('BWD @{} [{},{}]'.format(start,fwd,swd))
                    
                    J1 = blks[fwd][eui2]['tss']
                    J2 = blks[fwd][eui1]['tss']
                    J3 = blks[swd][eui2]['tss']
                    J4 = blks[swd][eui1]['tss']
                    
                    T31 = (J3 - J1) / 4294967296E9
                    T24 = (J2 - J4) / 4294967296E9
                    
                    Ga.append((T24,T31))
                    Ha.append((0))

        try:
            GG = np.array(Ga)
            HH = np.array(Ha)
            SS = lin.solve(dot(GG.T,GG),dot(GG.T,HH))

            Pab = SS[1] / SS[0]
            Cor = (SS[1] - SS[0]) / SS[0]
            C60 = int(Cor * (1<<60))

        except:
            pass

        print('{0}: {1:.6f} ppm'.format(i,Cor*1E6))
        
        
        if abs(Cor) < 10E-6:

            CrCNT += 1
            CrSUM += Cor
            CrSQR += Cor*Cor
        
            (fwd,bwd) = findFwdBwdPair(blks, eui1, eui2, i+j, 100)
            
            if bwd is not None and bwd == fwd + 1:

                ##print('BIDIR @{} [{},{}]'.format(start,fwd,bwd))
                    
                J1 = blks[fwd][eui1]['tss']
                J2 = blks[fwd][eui2]['tss']
                J3 = blks[bwd][eui2]['tss']
                J4 = blks[bwd][eui1]['tss']
                
                #T41 = (J4 - J1) / 4294967296E9
                #T23 = (J2 - J3) / 4294967296E9
                T41 = (J4 - J1)
                T23 = (J2 - J3)

                #print('T41: {}'.format(T41))
                #print('T23: {}'.format(T23))
                #print('C60: {}'.format(C60))

                DC = (C60*T23)>>60
                DD = (T41 + T23) + DC

                DdCNT += 1
                DdSUM += DD
                
                #print('DC: {}'.format(DC))
                #print('DD: {}'.format(DD))
                #print('Dj: {}'.format(Dj))
                
                Pa = Dj/DD
                Pb = Pa + Cor*Pa
                Fa = 1/Pa
                Fb = 1/Pb

                #print('Pa: {:.12f}'.format(Pa))
                #print('Pb: {:.12f}'.format(Pb))
                #print('{0} Fa:{1:.6f}GHz Fb:{2:.6f}GHz'.format(i,Fa,Fb))
                

    DdAVG = DdSUM / DdCNT

    CrAVG = CrSUM / CrCNT
    CrVAR = CrSQR / CrCNT - CrAVG * CrAVG
    CrSTD = math.sqrt(CrVAR)

    Pa = Dj / DdAVG
    Pb = Pa + CrAVG*Pa
    Fa = 1/Pa
    Fb = 1/Pb

    print('\nAVERAGE Fa:{:.6f}GHz Fb:{:.6f}GHz Cor:{:.3f}ppm'.format(Fa,Fb,CrAVG*1E6))


if __name__ == "__main__":
    main()

