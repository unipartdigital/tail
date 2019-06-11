#!/usr/bin/python3

import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot
import scipy.interpolate as interp

from pprint import pprint

Ch = 7
Pt = -10
Pi = math.pi
Cs = 299792458
Cl = 4*Pi/Cs
Fc = ( 3494.4, 3993.6, 4492,8, 3993.6, 6489.6, None, 6489.6 )

DAI = lambda m,fc,pt:    pt - 20*np.log10(m*fc*1e6*Cl)
ADI = lambda dBm,fc,pt:  10**((pt-dBm)/20) / (fc*1e6*Cl)


def DistComp(dist,txpwr,rxpwr,ch,prf):
    P = [ 0, 0, 0 ]
    if prf == 64:
        if ch in (4,7):
            if rxpwr < -90:
                P = [ 0.0183970957, 4.44641309, 227.515172 ]
            elif rxpwr < -70:
                P = [ 0.0444305694, 8.90189810, 417.601424 ]
            else:
                P = [ -0.03358327, -2.46361584,  4.70575174 ]
        else:
            if rxpwr < -95:
                P = [ 0.00167748918, 0.480519481, 21.9312229 ]
            elif rxpwr < -85:
                P = [ 0.0160714286, 3.20714286, 151.048214 ]
            elif rxpwr < -75:
                P = [ 0.0517857143, 9.06428571, 390.955357 ]
            elif rxpwr < -65:
                P = [ -0.0504464286, -6.34250000, -189.165625 ]
            else:
                P = [ -0.00483682984, -0.315687646, 9.83479021 ]
    C = np.polyval(P,rxpwr) / 100
    return dist + C


def DistCompLin(dist,txpwr,rxpwr,ch,prf):
    pass



RxCorrData = (
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

RxBetterData = (
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


C = np.array(RxCorrData)
D = np.array(RxBetterData)

XC = C[:,0] + 0.0
XD = D[:,0] + 0.0
XL = np.linspace(-120,-40,100)

C1 = 0.0 - C[:,1]
C2 = 0.0 - C[:,2]
C3 = 0.0 - C[:,3]
C4 = 0.0 - C[:,4]

D1 = 0.0 - D[:,1]
D2 = 0.0 - D[:,2]
D3 = 0.0 - D[:,3]
D4 = 0.0 - D[:,4]



## 900MHz/PRF64

XL40 = np.linspace(-120,-40,100)
XL41 = np.linspace(-120,-85,50)
XL42 = np.linspace(-90,-70,50)
XL43 = np.linspace(-70,-40,50)

PC40 = np.polyfit(XD[24:], D4[24:], 1)
PC41 = np.polyfit(XD[ 1:20], D4[ 1:20], 2)
PC42 = np.polyfit(XD[12:25], D4[12:25], 2)
PC43 = np.polyfit(XD[20:38], D4[20:38], 2)

CL40 = np.polyval(PC40,XL40)
CL41 = np.polyval(PC41,XL41)
CL42 = np.polyval(PC42,XL42)
CL43 = np.polyval(PC43,XL43)

print('#4: {}'.format(PC40))
print('#4 -120..-85: {}'.format(PC41))
print('#4  -90..-70: {}'.format(PC42))
print('#4  -70..-40: {}'.format(PC43))

CL4 = list(XL)
CT4 = list(XL)

for i in range(len(XL)):
    if XL[i] < -90:
        CL4[i] = np.polyval(PC41,XL[i])
    elif XL[i] < -70:
        CL4[i] = np.polyval(PC42,XL[i])
    else:
        CL4[i] = np.polyval(PC43,XL[i])
    
    CT4[i] = DistComp(0,0,XL[i],7,64) * 100

SC4 = interp.LSQUnivariateSpline(XL,CL4,[-105,-95,-85,-75,-65,-55])
CS4 = SC4(XL)

#for x in np.linspace(-115,-97,10):
#    print('{:.1f}, {:.1f}'.format(x,SC4(x)))

#for x in np.linspace(-59,-41,10):
#    print('{:.1f}, {:.1f}'.format(x,SC4(x)))



fig,ax = plot.subplots(1,1,figsize=(14,8),dpi=150)

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

#ax.plot(XC,C4,'.')
ax.plot(XD,D4,'.')
ax.plot(XL40,CL40)
ax.plot(XL41,CL41)
ax.plot(XL42,CL42)
ax.plot(XL43,CL43)
#ax.plot(XL,CL4)
#ax.plot(XL,CS4)
ax.plot(XL,CT4)

#plot.show()

#raise SystemExit


## 500MHz/PRF64

XL20 = np.linspace(-120,-40,100)
# ..-95
XL21 = np.linspace(-120,-95,50)
# -95..-85
XL22 = np.linspace(-95,-85,50)
# -85..-75
XL23 = np.linspace(-85,-75,50)
# -75..-65
XL24 = np.linspace(-75,-65,50)
# -65..
XL25 = np.linspace(-65,-40,50)

PC20 = np.polyfit(XD[24:], D2[24:], 1)
PC21 = np.polyfit(XD[3:12], D2[3:12], 2)
PC22 = np.polyfit(XD[10:17], D2[10:17], 2)
PC23 = np.polyfit(XD[15:22], D2[15:22], 2)
PC24 = np.polyfit(XD[20:26], D2[20:26], 2)
PC25 = np.polyfit(XD[25:36], D2[25:36], 2)

CL20 = np.polyval(PC20,XL20)
CL21 = np.polyval(PC21,XL21)
CL22 = np.polyval(PC22,XL22)
CL23 = np.polyval(PC23,XL23)
CL24 = np.polyval(PC24,XL24)
CL25 = np.polyval(PC25,XL25)

print('#2: {}'.format(PC20))

print('#2 -120..-95: {}'.format(PC21))
print('#2  -95..-85: {}'.format(PC22))
print('#2  -85..-75: {}'.format(PC23))
print('#2  -75..-65: {}'.format(PC24))
print('#2  -65..-40: {}'.format(PC25))

CL2 = list(XL)
CT2 = list(XL)
for i in range(len(XL)):
    if XL[i] < -95:
        CL2[i] = np.polyval(PC21,XL[i])
    elif XL[i] < -85:
        CL2[i] = np.polyval(PC22,XL[i])
    elif XL[i] < -75:
        CL2[i] = np.polyval(PC23,XL[i])
    elif XL[i] < -65:
        CL2[i] = np.polyval(PC24,XL[i])
    else:
        CL2[i] = np.polyval(PC25,XL[i])
    
    CT2[i] = DistComp(0,0,XL[i],5,64) * 100

SC2 = interp.LSQUnivariateSpline(XL,CL2,[-105,-95,-85,-75,-65,-55])
CS2 = SC2(XL)

#for x in np.linspace(-115,-97,10):
#    print('{:.1f}, {:.1f}'.format(x,np.polyval(PC21,x)))
#    print('{:.1f}, {:.1f}'.format(x,SC2(x)))

#for x in np.linspace(-59,-41,10):
#    print('{:.1f}, {:.1f}'.format(x,np.polyval(PC24,x)))
#    print('{:.1f}, {:.1f}'.format(x,SC2(x)))


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

#ax.plot(XC,C2,'.')
ax.plot(XD,D2,'.')
ax.plot(XL20,CL20)
ax.plot(XL21,CL21)
ax.plot(XL22,CL22)
ax.plot(XL23,CL23)
ax.plot(XL24,CL24)
ax.plot(XL25,CL25)
#ax.plot(XL,CL2)
#ax.plot(XL,CS2)
ax.plot(XL,CT2)

plot.show()

raise SystemExit


## Rest

fig,ax = plot.subplots(3,4,figsize=(20,10),dpi=80)

ax[0,0].set_title('6.5GHz/500MHz/PRF16')
ax[0,0].set_xlabel('[dBm]')
ax[0,0].set_ylabel('[cm]')

ax[0,1].set_title('6.5GHz/500MHz/PRF64')
ax[0,1].set_xlabel('[dBm]')
ax[0,1].set_ylabel('[cm]')

ax[0,2].set_title('6.5GHz/900MHz/PRF16')
ax[0,2].set_xlabel('[dBm]')
ax[0,2].set_ylabel('[cm]')

ax[0,3].set_title('6.5GHz/900MHz/PRF64')
ax[0,3].set_xlabel('[dBm]')
ax[0,3].set_ylabel('[cm]')


ax[0,0].grid(True)
ax[0,0].plot(XC,C1,'.-')
ax[0,1].grid(True)
ax[0,1].plot(XC,C2,'.-')
ax[0,2].grid(True)
ax[0,2].plot(XC,C3,'.-')
ax[0,3].grid(True)
ax[0,3].plot(XC,C4,'.-')

ax[1,0].grid(True)
#ax[1,0].plot(XL,CL1)

ax[1,1].grid(True)
#ax[1,1].plot(XL,CL2)

ax[1,2].grid(True)
#ax[1,2].plot(XL,CL3)

ax[1,3].grid(True)
ax[1,3].plot(XC,C4,'.')
ax[1,3].plot(XL,CL4)

plot.show()

