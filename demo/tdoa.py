#!/usr/bin/python3
#
# TDOA lateration library for Tail
#

import math
import numpy as np
import numpy.linalg as lin

from numpy import dot


## Functions

def dsq(a):
    return np.sum((a*a).T,0)

def norm(a):
    return np.sqrt(dsq(a))

def dist(x,y):
    return norm(x-y)

def hypercone(b0,bi,di):
    bi0 = bi - b0
    di0 = di.reshape(-1,1)
    Gb = np.block([bi0,di0])
    hb = (dsq(bi)-dsq(b0)-di*di)/2
    Gbb = dot(Gb.T,Gb)
    Gbh = dot(Gb.T,hb)
    x = lin.solve(Gbb,Gbh)
    return x[0:3]

def hyperjump(b0,bs,bi,di,sigma,theta):
    bi0 = bi - b0
    bs0 = bs - b0
    ds0 = norm(bs0)
    dis = norm(bi - bs)
    di0 = di.reshape(-1,1)
    Gb = np.block([[bi0,di0],[bs0,-ds0],[bs[1],-bs[0],0,0],[bs[2],0,-bs[0],0]])
    hb = np.block([(dsq(bi)-dsq(b0)-di*di)/2, dot(bs0.T,b0), 0, 0])
    Cv = ds0*theta
    Cc = ds0*theta*theta/2
    Pm = dis*sigma
    Ps = np.block([1/Pm,1/Cc,1/Cv,1/Cv])
    Gs = np.diag(Ps*Ps)
    Gbb = dot(dot(Gb.T,Gs),Gb)
    Gbh = dot(dot(Gb.T,Gs),hb)
    x = lin.solve(Gbb,Gbh)
    c = lin.cond(Gbb)
    return x[0:3],c


def hyperlater(ref_coord,coords,ranges,sigmas,delta=None,theta=0.045,maxiter=8):
    if len(coords) < 5:
        raise np.linalg.LinAlgError('Not enough inputs: {}'.format(len(coords)))
    B0 = np.array(ref_coord)
    B = np.array(coords)
    R = np.array(ranges)
    S = np.array(sigmas)
    X = hypercone(B0,B,R)
    Y,C = hyperjump(B0,X,B,R,S,theta)
    if delta is None:
        delta = np.amin(S) / 2
    N = 1
    while N < maxiter and dist(X,Y) > delta:
        X = Y
        N = N + 1
        Y,C = hyperjump(B0,X,B,R,S,theta)
    return Y,C


def hypersigmas(X0,B0,R0,A,L,Ch,Pwr):
    N = len(A)
    S = np.zeros(N)
    Dxr = dist(X0,R0)
    Dbr = dist(B0,R0)
    Rxb = RFCalcRxPower(Ch,Dxb,Pwr)
    Rrb = RFCalcRxPower(Ch,Drb,Pwr)
    for i in range(N):
        Li = L[i]
        Dxi = dist(X0,A[i])
        Dbi = dist(B0,A[i])
        Rxi = RFCalcRxPower(Ch,Dxi,Pwr)
        Rbi = RFCalcRxPower(Ch,Dbi,Pwr)
    return S
    
def hyperlater_rfcomp(beacon_coord,ref_coord,coords,ranges,rflevels,channel=5,power=-12.3,delta=None,theta=0.045,maxiter=8):
    if len(coords) < 5:
        raise np.linalg.LinAlgError('Not enough inputs: {}'.format(len(coords)))
    B0 = np.array(beacon_coord)
    R0 = np.array(ref_coord)
    A = np.array(coords)
    R = np.array(ranges)
    L = np.array(rflevels)
    X = hypercone(R0,A,R)
    S = hypersigmas(X,B0,R0,A,L,channel,power)
    Y,C = hyperjump(R0,X,A,R,S,theta)
    S = hypersigmas(Y,B0,R0,A,L,channel)
    if delta is None:
        delta = np.amin(S) / 2
    N = 1
    while N < maxiter and dist(X,Y) > delta:
        X = Y
        N = N + 1
        Y,C = hyperjump(R0,X,A,R,S,theta)
        S = hypersigmas(Y,B0,R0,A,L,channel,power)
    return Y,C

