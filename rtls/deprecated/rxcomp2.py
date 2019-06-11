#!/usr/bin/python3

import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot
import scipy.interpolate as interp



##
## Compensation model - result of this script
##

SPLINES = {
    900: {
        16: [
        ],
        64: [
             ((-120.0, -87.0), (234.44955675228655, 4.595272619389899, 0.019180011283998155)),
             (( -87.0, -71.0), (372.2527652467459, 7.762418365235941, 0.0373777099403898)),
             (( -71.0, -40.0), (-8.653981898307872, -2.9650299671686025, -0.03815131977980646)),
        ],
    },
    500: {
        16: [
        ],
        64: [
        ],
    },
}


def XSpliner(X,Y,borders,ranges):
    NC = 3     # Order
    W0 = 100   # C0 weight
    W1 = 100   # C1 weight
    NR = len(ranges)
    NL = NR*NC
    GX = np.empty((0,NL))
    GY = np.empty((0,1))
    I = 0
    for R in ranges:
        L = np.zeros((1,NL))
        D = np.zeros((1,1))
        print(R[0])
        print(R[1])
        for i in range(R[0],R[1]):
            print(i)
            x,y = X[i],Y[i]
            D[0,0] = Y[i]
            L[0,I+0] = 1
            L[0,I+1] = X[i]
            L[0,I+2] = X[i]*X[i]
            GX = np.vstack((GX,L))
            GY = np.vstack((GY,D))
        I += NC
    for j in range(NR-1):
        L = np.zeros((1,NL))
        D = np.zeros((1,1))
        I = j*NC
        x = borders[j+1]
        L[0,I+0] = W0
        L[0,I+1] = W0*x
        L[0,I+2] = W0*x*x
        L[0,I+3] = -W0
        L[0,I+4] = -W0*x
        L[0,I+5] = -W0*x*x
        GX = np.vstack((GX,L))
        GY = np.vstack((GY,D))
    for j in range(NR-1):
        L = np.zeros((1,NL))
        D = np.zeros((1,1))
        I = j*NC
        x = borders[j+1]
        L[0,I+1] = W0
        L[0,I+2] = W0*2*x
        L[0,I+4] = -W0
        L[0,I+5] = -W0*2*x
        GX = np.vstack((GX,L))
        GY = np.vstack((GY,D))
    (SP,_,_,_) = lin.lstsq(GX,GY,rcond=None)
    SPL = [[ [borders[j],borders[j+1]], [SP[j*NC+i][0] for i in range(NC)] ] for j in range(NR) ]
    return SPL


def XSpline(spline,X):
    for S in spline:
        if S[0][0] < X <= S[0][1]:
            Y = S[1][0] + S[1][1]*X + S[1][2]*X*X
            return Y
    return None


def DistComp(dist,txpwr,rxpwr,ch,prf):
    if ch in (4,7):
        rfw = 900
    else:
        rfw = 500
    SPL = SPLINES[rfw][prf]
    COR = XSpline(SPL,dist)
    return COR



##
## RF Propagation model
##

Pi = math.pi
Cs = 299792458
Cl = 4*Pi/Cs
Fc = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )

DAI = lambda m,fc,pt:    pt - 20*np.log10(m*fc*1e6*Cl)
ADI = lambda dBm,fc,pt:  10**((pt-dBm)/20) / (fc*1e6*Cl)



##
## Input data from Decawave datasheet
##

RxCorrectionData = (
    # RSL, 16/500,64/500,16/900,64/900, 
    (-95,  11.5,   8.5,  39.4,  28.4), #1
    (-93,  11.0,   8.1,  35.6,  26.4),
    (-91,  10.6,   7.6,  33.9,  24.5),
    (-89,   9.7,   7.1,  32.1,  23.3),
    (-87,   8.4,   6.2,  29.4,  19.7), #5
    (-85,   6.5,   4.9,  25.4,  17.5),
    (-83,   3.6,   4.2,  21.0,  15.3),
    (-81,   0.0,   3.5,  15.8,  12.7),
    (-79,  -3.1,   2.1,   9.7,   9.1),
    (-77,  -5.9,   0.0,   4.2,   4.9), #10
    (-75,  -8.4,  -2.7,   0.0,   0.0),
    (-73, -10.9,  -5.1,  -5.1,  -5.8),
    (-71, -12.7,  -6.9,  -9.5, -10.0),
    (-69, -14.3,  -8.2, -13.8, -15.0),
    (-67, -16.3,  -9.3, -17.6, -19.9), #15
    (-65, -17.9, -10.0, -21.0, -23.5),
    (-63, -18.7, -10.5, -24.4, -26.6),
    (-61, -19.8, -11.0, -27.5, -29.5), #18
)

RxExtendedData = (
    (-115,  0.0,  11.1,   0.0,  40.4), #1
    (-113,  0.0,  10.9,   0.0,  39.9),
    (-111,  0.0,  10.7,   0.0,  39.4),
    (-109,  0.0,  10.5,   0.0,  38.6),
    (-107,  0.0,  10.3,   0.0,  37.8), #5
    (-105,  0.0,  10.0,   0.0,  36.7),
    (-103,  0.0,   9.8,   0.0,  35.4),
    (-101,  0.0,   9.5,   0.0,  33.9),
    (-99,   0.0,   9.2,   0.0,  32.3),
    (-97,   0.0,   8.9,   0.0,  30.6), #10
    (-95,  11.0,   8.5,  39.0,  28.4), #11 FirstReal
    (-93,  10.5,   8.3,  36.8,  26.4),
    (-91,   9.8,   7.8,  34.2,  24.5),
    (-89,   8.9,   7.1,  32.1,  23.3),
    (-87,   7.8,   6.2,  29.4,  19.7), #15
    (-85,   6.0,   5.4,  25.4,  17.5),
    (-83,   3.6,   4.5,  21.0,  15.3),
    (-81,   0.0,   3.5,  15.8,  12.7),
    (-79,  -3.1,   2.1,   9.7,   9.1),
    (-77,  -5.9,   0.0,   4.2,   4.9), #20
    (-75,  -8.4,  -2.7,   0.0,   0.0),
    (-73, -10.9,  -5.1,  -5.1,  -5.8),
    (-71, -12.7,  -6.9,  -9.5, -10.0),
    (-69, -14.3,  -8.2, -13.8, -15.0),
    (-67, -16.3,  -9.3, -17.6, -19.9), #25
    (-65, -17.9, -10.0, -21.0, -23.5),
    (-63, -18.7, -10.5, -24.4, -26.6),
    (-61, -19.8, -11.0, -27.5, -29.5), #28 LastReal
    (-59,   0.0, -11.6,   0.0, -33.2),
    (-57,   0.0, -12.1,   0.0, -35.9), #30
    (-55,   0.0, -12.6,   0.0, -38.4),
    (-53,   0.0, -13.0,   0.0, -40.7),
    (-51,   0.0, -13.4,   0.0, -42.8),
    (-49,   0.0, -13.7,   0.0, -44.7),
    (-47,   0.0, -14.0,   0.0, -46.4),
    (-45,   0.0, -14.2,   0.0, -47.7),
    (-43,   0.0, -14.4,   0.0, -48.7),
    (-41,   0.0, -14.5,   0.0, -49.3), #38
)


##
## Data points
##

C = np.array(RxCorrectionData)
D = np.array(RxExtendedData)

XC = C[:,0] + 0.0
XD = D[:,0] + 0.0

C1 = 0.0 - C[:,1]
C2 = 0.0 - C[:,2]
C3 = 0.0 - C[:,3]
C4 = 0.0 - C[:,4]

D1 = 0.0 - D[:,1]
D2 = 0.0 - D[:,2]
D3 = 0.0 - D[:,3]
D4 = 0.0 - D[:,4]



######################################################################################
##
## 900MHz/PRF64
##
######################################################################################

## Custom Spline

# Number of coeffs (order + 1)
NC = 3

# Range borders
CX = ( -120, XD[14], XD[22], -40 )

# Range data points
RX = ( (1,20), (12,25), (20,38) )

# Input data
XD41 = XD[ 1:20]
YD41 = D4[ 1:20]
XD42 = XD[12:25]
YD42 = D4[12:25]
XD43 = XD[20:38]
YD43 = D4[20:38]

# Input arrays
XX = ( XD41, XD42, XD43 )
YY = ( YD41, YD42, YD43 )

# Weights
WG = ( 100, 100 )

# Number of segments
NR = len(XX)

# Line length
NX = NR*NC

# Spline matrix
GX = np.empty((0,NX))
GY = np.empty((0,1))


## Segments

for P in range(NR):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    for Q in range(len(XX[P])):
        X = XX[P][Q]
        Y = YY[P][Q]
        I = P*NC
        GL[0,I+0] = 1
        GL[0,I+1] = X
        GL[0,I+2] = X*X
        GD[0,0] = Y
        GX = np.vstack((GX,GL))
        GY = np.vstack((GY,GD))

W0 = WG[0]
for P in range(NR-1):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    X = CX[P+1]
    I = P*NC
    GL[0,I+0] = W0
    GL[0,I+1] = W0*X
    GL[0,I+2] = W0*X*X
    GL[0,I+3] = -W0
    GL[0,I+4] = -W0*X
    GL[0,I+5] = -W0*X*X
    GX = np.vstack((GX,GL))
    GY = np.vstack((GY,GD))
    
W1 = WG[1]
for P in range(NR-1):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    X = CX[P+1]
    I = P*NC
    GL[0,I+1] = W0
    GL[0,I+2] = 2*W0*X
    GL[0,I+4] = -W0
    GL[0,I+5] = -2*W0*X
    GX = np.vstack((GX,GL))
    GY = np.vstack((GY,GD))


## Final spline

(SP,_,_,_) = lin.lstsq(GX,GY,rcond=None)

#SPL = [[ [CX[j],CX[j+1]], [SP[j*NC+i][0] for i in range(NC)] ] for j in range(NR) ]
#print(SPL)

SPL = XSpliner(XD,D4,CX,RX)




##
## Plot
##

XXX = np.linspace(-115,-40,100)
YYY = np.zeros(100)
ZZZ = np.zeros(100)

for i in range(len(XXX)):
    YYY[i] = XSpline(SPL,XXX[i])
    ZZZ[i] = DistComp(XXX[i],None,None,7,64)


fig,ax = plot.subplots(1,1,figsize=(10,6),dpi=150)

ax.set_title('900MHZ/PRF64')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[cm]')

ax.set_xlim([-120,-40])
ax.set_ylim([-60,60])

ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-60,60,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-60,60,2), minor=True )

ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)

ax.plot(XD,D4,'.')
ax.plot(XXX,YYY)
ax.plot(XXX,ZZZ)


######################################################################################

#plot.show()
#raise SystemExit




######################################################################################
##
## 500MHz/PRF64
##
######################################################################################

## Custom Spline

# Number of coeffs (order + 1)
NC = 3

# Continuation points
CX = ( -120, XD[11], XD[16], XD[21], XD[25], -40 )

# Input X data
XD21 = XD[ 3:12]
XD22 = XD[10:17]
XD23 = XD[15:22]
XD24 = XD[20:26]
XD25 = XD[25:36]

# Input Y data
YD21 = D2[ 3:12]
YD22 = D2[10:17]
YD23 = D2[15:22]
YD24 = D2[20:26]
YD25 = D2[25:36]

# Input arrays
XX = ( XD21, XD22, XD23, XD24, XD25 )
YY = ( YD21, YD22, YD23, YD24, YD25 )

# Weights
WG = ( 100, 100 )

# Number of segments
NR = len(XX)

# Line length
NX = NR*NC

# Spline matrix
GX = np.empty((0,NX))
GY = np.empty((0,1))


## Segments

for P in range(NR):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    for Q in range(len(XX[P])):
        X = XX[P][Q]
        Y = YY[P][Q]
        I = P*NC
        GL[0,I+0] = 1
        GL[0,I+1] = X
        GL[0,I+2] = X*X
        GD[0,0] = Y
        GX = np.vstack((GX,GL))
        GY = np.vstack((GY,GD))

W0 = WG[0]
for P in range(NR-1):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    X = CX[P+1]
    I = P*NC
    GL[0,I+0] = W0
    GL[0,I+1] = W0*X
    GL[0,I+2] = W0*X*X
    GL[0,I+3] = -W0
    GL[0,I+4] = -W0*X
    GL[0,I+5] = -W0*X*X
    GX = np.vstack((GX,GL))
    GY = np.vstack((GY,GD))
    
W1 = WG[1]
for P in range(NR-1):
    GL = np.zeros((1,NX))
    GD = np.zeros((1,1))
    X = CX[P+1]
    I = P*NC
    GL[0,I+1] = W0
    GL[0,I+2] = 2*W0*X
    GL[0,I+4] = -W0
    GL[0,I+5] = -2*W0*X
    GX = np.vstack((GX,GL))
    GY = np.vstack((GY,GD))


## Final spline

(SP,_,_,_) = lin.lstsq(GX,GY,rcond=None)

SPL = [[ [CX[j],CX[j+1]], [SP[j*NC+i][0] for i in range(NC)] ] for j in range(NR) ]

print(SPL)



##
## Plot
##

fig,ax = plot.subplots(1,1,figsize=(14,8),dpi=150)

ax.set_title('500MHZ/PRF64')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[cm]')

ax.set_xlim([-120,-40])
ax.set_ylim([-25,25])

ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-20,20,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-20,20,2), minor=True )

ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)

ax.plot(XD,D2,'.')

XL = np.linspace(-115,-40,100)
YL = np.zeros(100)

for R in range(NR):
    XL = np.linspace(CX[R],CX[R+1],100)
    for i in range(100):
        YL[i] = XSpline(SPL,XL[i])
        #ZL[i] = DistComp(XL[i],None,None,5,64)
    ax.plot(XL,YL)




######################################################################################

plot.show()
raise SystemExit
