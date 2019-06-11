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
    500: {
        16: (
             ((-95.0, -89.0), (455.2684032227685, 9.851533848614533, 0.051993231111100435)),
             ((-89.0, -81.0), (622.1582642485359, 13.601867408230925, 0.07306251852581003)),
             ((-81.0, -75.0), (-206.63577569900568, -6.862181359285285, -0.05325876022235132)),
             ((-75.0, -69.0), (-14.553074442797616, -1.7399765082001553, -0.019110731344085252)),
             ((-69.0, -61.0), (-65.34665835419767, -3.212254801451526, -0.02977941823739272)),
        ),
        64: (
              ((-105.0, -91.0), (60.352219498834565, 1.259091772638299, 0.005614160222348175)),
              (( -91.0, -81.0), (182.24644860110973, 3.938085215997636, 0.020333901101900254)),
              (( -81.0, -75.0), (416.4655048521236, 9.72127075199398, 0.05603257081757784)),
              (( -75.0, -67.0), (-235.36598188854484, -7.660900913339617, -0.05984856478355027)),
              (( -67.0, -55.0), (-15.291050806896337, -1.0915006691080062, -0.010823194973097472)),
        ),
    },
    900: {
        16: (
             ((-95.0, -89.0), (183.67480691132866, 3.6158987280067723, 0.013391462077503746)),
             ((-89.0, -81.0), (909.6294873191769, 19.92948671225841, 0.10504083084258342)),
             ((-81.0, -75.0), (-79.62234302197686, -4.496483922533177, -0.0457367625993812)),
             ((-75.0, -69.0), (47.94037800579669, -1.094811223380935, -0.023058943654632458)),
             ((-69.0, -61.0), (-95.74259549796217, -5.259534749105479, -0.05323809715869743))            
        ),
        64: (
             ((-105.0, -95.0), (216.3308306122728, 4.1714254724783855, 0.01677363406513388)),
             (( -95.0, -83.0), (148.11352408935457, 2.7353156634156304, 0.009215393273090733)),
             (( -83.0, -75.0), (732.1532410581545, 16.808623222604062, 0.09399472336764236)),
             (( -75.0, -67.0), (-20.421159267426496, -3.260069209064098, -0.039796838878970675)),
             (( -67.0, -61.0), (-96.7161189002168, -5.537443600292282, -0.0567915127387808)),
             (( -61.0, -55.0), (5.839529695372041, -2.1750623191076377, -0.029231829906617435)),
        ),
    },
}


def XSpliner(X,Y,borders,ranges):
    NC = 3      # Order
    W0 = 1000   # C0 weight
    W1 = 1000   # C1 weight
    NR = len(ranges)
    NL = NR*NC
    GX = np.empty((0,NL))
    GY = np.empty((0,1))
    I = 0
    for R in ranges:
        L = np.zeros((1,NL))
        D = np.zeros((1,1))
        for i in range(R[0],R[1]):
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
    SPL = [[[borders[j],borders[j+1]], [SP[j*NC+i][0] for i in range(NC)]] for j in range(NR)]
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
    (-95,  11.5,   8.5,  39.4,  28.4), #0
    (-93,  11.0,   8.1,  35.6,  26.4),
    (-91,  10.6,   7.6,  33.9,  24.5),
    (-89,   9.7,   7.1,  32.1,  23.3),
    (-87,   8.4,   6.2,  29.4,  19.7),
    (-85,   6.5,   4.9,  25.4,  17.5), #5
    (-83,   3.6,   4.2,  21.0,  15.3),
    (-81,   0.0,   3.5,  15.8,  12.7),
    (-79,  -3.1,   2.1,   9.7,   9.1),
    (-77,  -5.9,   0.0,   4.2,   4.9),
    (-75,  -8.4,  -2.7,   0.0,   0.0), #10
    (-73, -10.9,  -5.1,  -5.1,  -5.8),
    (-71, -12.7,  -6.9,  -9.5, -10.0),
    (-69, -14.3,  -8.2, -13.8, -15.0),
    (-67, -16.3,  -9.3, -17.6, -19.9),
    (-65, -17.9, -10.0, -21.0, -23.5), #15
    (-63, -18.7, -10.5, -24.4, -26.6),
    (-61, -19.8, -11.0, -27.5, -29.5), #17
)

RxExtendedData = (
    (-115,  0.0,  11.1,   0.0,  40.4), #0
    (-113,  0.0,  10.9,   0.0,  39.9),
    (-111,  0.0,  10.7,   0.0,  39.4),
    (-109,  0.0,  10.5,   0.0,  38.6),
    (-107,  0.0,  10.3,   0.0,  37.8),
    (-105,  0.0,  10.0,   0.0,  36.7), #5
    (-103,  0.0,   9.8,   0.0,  35.4),
    (-101,  0.0,   9.5,   0.0,  33.9),
    (-99,   0.0,   9.2,   0.0,  32.3),
    (-97,   0.0,   8.9,   0.0,  30.6), #9
    (-95,  11.5,   8.5,  39.0,  28.4), #10 FirstReal
    (-93,  11.0,   8.3,  36.8,  26.4),
    (-91,  10.6,   7.8,  34.2,  24.5),
    (-89,   9.7,   7.1,  32.1,  22.3),
    (-87,   8.4,   6.2,  29.4,  19.7),
    (-85,   6.5,   5.4,  25.4,  17.5), #15
    (-83,   3.6,   4.5,  21.0,  15.3),
    (-81,   0.0,   3.5,  15.8,  12.7),
    (-79,  -3.1,   2.1,   9.7,   9.1),
    (-77,  -5.9,   0.0,   4.2,   4.9),
    (-75,  -8.4,  -2.7,   0.0,   0.0), #20
    (-73, -10.9,  -5.1,  -5.1,  -5.8),
    (-71, -12.7,  -6.9,  -9.5, -10.0),
    (-69, -14.3,  -8.2, -13.8, -15.0),
    (-67, -16.3,  -9.3, -17.6, -19.9), 
    (-65, -17.9, -10.0, -21.0, -23.5), #25
    (-63, -18.7, -10.5, -24.4, -26.6),
    (-61, -19.8, -11.0, -27.5, -29.5), #27 LastReal
    (-59,   0.0, -11.4,   0.0, -32.5),
    (-57,   0.0, -11.8,   0.0, -35.0), 
    (-55,   0.0, -12.0,   0.0, -37.0), #30
    (-53,   0.0, -12.3,   0.0, -39.0),
    (-51,   0.0, -12.6,   0.0, -40.5), #32
)


##
## Data points
##

C = np.array(RxCorrectionData)
D = np.array(RxExtendedData)

XC = 0.0 + C[:,0]
XD = 0.0 + D[:,0]

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
## 500MHz/PRF16
##
######################################################################################

## Custom Spline

# Ranges
CX = ( XD[10], XD[13], XD[17], XD[20], XD[23], XD[27], )
RX = ( (10,14), (12,18), (16,21), (19,24), (23,27), )

# Calculate Spline
SPL = XSpliner(XD,D1,CX,RX)
#print(SPL)

# Plot
fig,ax = plot.subplots(1,1,figsize=(14,9),dpi=150)

ax.set_title('500MHZ/PRF16')
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

ax.plot(XD,D1,'.')
ax.plot(XC,C1,'*')

for i in range(len(RX)):
    XL = np.linspace(CX[i],CX[i+1],100)
    YL = np.zeros(100)
    ZL = np.zeros(100)
    for i in range(100):
        YL[i] = XSpline(SPL,XL[i])
        ZL[i] = DistComp(XL[i],None,None,1,16)
    ax.plot(XL,YL)
    #ax.plot(XL,ZL)


######################################################################################

#plot.show()
#raise SystemExit



######################################################################################
##
## 900MHz/PRF16
##
######################################################################################

## Custom Spline

# Ranges
CX = ( XD[10], XD[13], XD[17], XD[20], XD[23], XD[27] )
RX = ( (10,14), (12,18), (16,21), (19,24), (23,27) )

# Calculate Spline
SPL = XSpliner(XD,D3,CX,RX)
#print(SPL)

# Plot
fig,ax = plot.subplots(1,1,figsize=(14,9),dpi=150)

ax.set_title('900MHZ/PRF16')
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

ax.plot(XD,D3,'.')
ax.plot(XC,C3,'*')

for i in range(len(RX)):
    XL = np.linspace(CX[i],CX[i+1],100)
    YL = np.zeros(100)
    ZL = np.zeros(100)
    for i in range(100):
        YL[i] = XSpline(SPL,XL[i])
        ZL[i] = DistComp(XL[i],None,None,7,16)
    ax.plot(XL,YL)
    #ax.plot(XL,ZL)


######################################################################################

#plot.show()
#raise SystemExit



######################################################################################
##
## 500MHz/PRF64
##
######################################################################################

## Custom Spline

# Ranges
#CX = ( XD[5], XD[11], XD[16], XD[19], XD[21], XD[24], XD[27], XD[30] )
#RX = ( (5,11), (10,17), (15,20), (18,22), (20,25), (23,28), (26,30) )
#CX = ( XD[5], XD[12], XD[16], XD[20], XD[24], XD[27], XD[30])
#RX = ( (5,13), (11,17), (15,21), (19,25), (23,28), (26,31) )
CX = ( XD[5], XD[12], XD[17], XD[20], XD[24], XD[30])
RX = ( (5,13), (11,18), (16,21), (19,25), (23,31) )

# Calculate Spline
SPL = XSpliner(XD,D2,CX,RX)
#print(SPL)

# Plot
fig,ax = plot.subplots(1,1,figsize=(14,9),dpi=150)

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
ax.plot(XC,C2,'*')

for i in range(len(RX)):
    XL = np.linspace(CX[i],CX[i+1],100)
    YL = np.zeros(100)
    ZL = np.zeros(100)
    for i in range(100):
        YL[i] = XSpline(SPL,XL[i])
        ZL[i] = DistComp(XL[i],None,None,5,64)
    ax.plot(XL,YL)
    ax.plot(XL,ZL)


######################################################################################

#plot.show()
#raise SystemExit



######################################################################################
##
## 900MHz/PRF64
##
######################################################################################

## Custom Spline

# Ranges
#CX = ( XD[5], XD[10], XD[16], XD[20], XD[24], XD[27], XD[30] )
#RX = ( (5,11), (10,16), (16,20), (20,24), (24,27), (26,32) )
#CX = ( XD[5], XD[12], XD[15], XD[20], XD[24], XD[27], XD[30] )
#RX = ( (5,13), (12,15), (15,20), (20,24), (24,27), (26,32) )
#CX = ( XD[5], XD[15], XD[20], XD[24], XD[27], XD[30] )
#RX = ( (4,16), (15,21), (19,24), (24,27), (26,32) )
#CX = ( XD[5], XD[15], XD[20], XD[25], XD[30] )
#RX = ( (4,16), (15,21), (19,25), (24,32) )
CX = ( XD[5], XD[11], XD[16], XD[20], XD[23], XD[26], XD[30] )
RX = ( (5,12), (10,16), (15,21), (19,24), (23,26), (25,32) )

# Calculate Spline
SPL = XSpliner(XD,D4,CX,RX)
#print(SPL)

# Plot
fig,ax = plot.subplots(1,1,figsize=(14,9),dpi=150)

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
ax.plot(XC,C4,'*')

for i in range(len(RX)):
    XL = np.linspace(CX[i],CX[i+1],100)
    YL = np.zeros(100)
    ZL = np.zeros(100)
    for i in range(100):
        YL[i] = XSpline(SPL,XL[i])
        ZL[i] = DistComp(XL[i],None,None,7,64)
    ax.plot(XL,YL)
    ax.plot(XL,ZL)


######################################################################################

plot.show()
#raise SystemExit


