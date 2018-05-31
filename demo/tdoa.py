#!/usr/bin/python3

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
    return x[0:3]

def hyperlater(B,R,S,delta=None,theta=0.045,maxiter=8):
    N = 1
    I = np.argsort(R)
    I0,Ii = I[0],I[1:]
    B0,Bi = B[I0],B[Ii]
    R0,Ri = R[I0],R[Ii]
    Ri0 = Ri-R0
    Si0 = S[Ii]+S[I0]
    X = hypercone(B0,Bi,Ri0)
    Y = hyperjump(B0,X,Bi,Ri0,Si0,theta)
    if delta is None:
        delta = np.amin(S)
    while N < maxiter and dist(X,Y) > delta:
        Y,X,N = hyperjump(B0,Y,Bi,Ri0,Si0,theta),Y,N+1
    return Y,N

