#!/usr/bin/python3
#
# TDOA lateration library for Tail
#

import math
import numpy as np
import numpy.linalg as lin

from dwarf import *
from numpy import dot


## Functions

def dsq(a):
    return np.sum((a*a).T,0)

def norm(a):
    return np.sqrt(dsq(a))

def dist(x,y):
    return norm(x-y)

def hypercone(b0,bi,di):
    dim = len(b0)
    bi0 = bi - b0
    di0 = di.reshape(-1,1)
    Gb = np.block([bi0,di0])
    hb = (dsq(bi)-dsq(b0)-di*di)/2
    Gbb = dot(Gb.T,Gb)
    Gbh = dot(Gb.T,hb)
    X = lin.solve(Gbb,Gbh)
    return X[0:dim]

def hyperjump2D(b0,bs,bi,di,sigma,theta):
    bi0 = bi - b0
    bs0 = bs - b0
    ds0 = norm(bs0)
    dis = norm(bi - bs)
    di0 = di.reshape(-1,1)
    Gb = np.block([[bi0,di0],[bs0,-ds0],[bs[1],-bs[0],0]])
    hb = np.block([(dsq(bi)-dsq(b0)-di*di)/2, dot(bs0.T,b0), 0])
    Cv = ds0*theta
    Cc = ds0*theta*theta/2
    Pm = dis*sigma
    Ps = np.block([1/Pm,1/Cc,1/Cv])
    Gs = np.diag(Ps*Ps)
    Gbb = dot(dot(Gb.T,Gs),Gb)
    Gbh = dot(dot(Gb.T,Gs),hb)
    X = lin.solve(Gbb,Gbh)
    C = lin.cond(Gbb)
    return X[0:2],C

def hyperjump3D(b0,bs,bi,di,sigma,theta):
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
    X = lin.solve(Gbb,Gbh)
    C = lin.cond(Gbb)
    return X[0:3],C

def hyperlater2D(ref_coord,coords,ranges,sigmas,delta=None,theta=0.045,maxiter=8):
    if len(coords) < 3:
        raise np.linalg.LinAlgError('Not enough inputs: {}'.format(len(coords)))
    B0 = np.array(ref_coord)[0:2]
    B = np.array(coords)[:,0:2]
    R = np.array(ranges)
    S = np.array(sigmas)
    X = hypercone(B0,B,R)
    Y,C = hyperjump2D(B0,X,B,R,S,theta)
    if delta is None:
        delta = np.amin(S) / 2
    N = 1
    while N < maxiter and dist(X,Y) > delta:
        X = Y
        N = N + 1
        Y,C = hyperjump2D(B0,X,B,R,S,theta)
    X = np.array((Y[0],Y[1],0))
    return X,C

def hyperlater3D(ref_coord,coords,ranges,sigmas,delta=None,theta=0.045,maxiter=8):
    if len(coords) < 4:
        raise np.linalg.LinAlgError('Not enough inputs: {}'.format(len(coords)))
    B0 = np.array(ref_coord)
    B = np.array(coords)
    R = np.array(ranges)
    S = np.array(sigmas)
    X = hypercone(B0,B,R)
    Y,C = hyperjump3D(B0,X,B,R,S,theta)
    if delta is None:
        delta = np.amin(S) / 2
    N = 1
    while N < maxiter and dist(X,Y) > delta:
        X = Y
        N = N + 1
        Y,C = hyperjump3D(B0,X,B,R,S,theta)
    return Y,C


def hyperlater(ref_coord,coords,ranges,sigmas,delta=None,theta=0.045,maxiter=8):
    return hyperlater3D(ref_coord,coords,ranges,sigmas,delta,theta,maxiter)

