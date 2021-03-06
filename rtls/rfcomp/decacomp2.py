#!/usr/bin/python3

import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot
import scipy.interpolate as interp


## Config values

Ch  = 7
Prf = 64

Atten = {
    1: -14.0,
    2: -14.0,
    3: -14.0,
    4: -11.5,
    5: -14.0,
    7: -11.0,
}


## Constants

Pi = math.pi
Cs = 299792458
Fc = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )

Cc = 4*Pi/Cs

DAI = lambda m,fc,pt: pt - 20*np.log10(m*Cc*fc*1e6)
ADI = lambda dBm,fc,pt: 10**((pt-dBm)/20)/(Cc*fc*1e6)


## Compensation values from Decawave implementation

OffsetBase = {
    16:{
        1: -23,
        2: -23,
        3: -23,
        4: -28,
        5: -23,
        7: -28,
    },
    64:{
        1: -17,
        2: -17,
        3: -17,
        4: -30,
        5: -17,
        7: -30,
    },
}

OffsetData = {
    16:{
        1:(
            3, 4, 5, 7, 9, 11, 12, 13, 15, 18, 20, 23, 25,
            28, 30, 33, 36, 40, 43, 47, 50, 54, 58, 63, 66,
            71, 76, 82, 89, 98, 109, 127, 155, 222, 255,
        ),
        2:(
            1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 15, 18, 20, 22,
            24, 27, 29, 32, 35, 38, 41, 44, 47, 51, 55, 58,
            62, 66, 71, 78, 85, 96, 111, 135, 194, 240,
        ),
        3:(
            1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 14, 16, 18, 20,
            22, 24, 26, 28, 31, 33, 36, 39, 42, 45, 49, 52,
            55, 59, 63, 69, 76, 85, 98, 120, 173, 213,
        ),
        4:(
            7, 7, 8, 9, 9, 10, 11, 11, 12, 13, 14, 15, 16,
            17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 30,
            31, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52,
            55, 57, 59, 61, 63, 66, 68, 71, 74, 78, 81, 85,
            89, 94, 99, 104, 110, 116, 123, 130, 139, 150,
            164, 182, 207, 238, 255,
        ),
        5:(
            1, 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 11, 12, 14,
            15, 16, 18, 20, 21, 23, 25, 27, 29, 31, 34, 36,
            38, 41, 44, 48, 53, 59, 68, 83, 120, 148,
        ),
        7:(
            4, 5, 5, 5, 6, 6, 7, 7, 7, 8, 9, 9, 10, 10,
            11, 11, 12, 13, 13, 14, 15, 16, 17, 17, 18,
            19, 20, 21, 22, 23, 25, 26, 27, 29, 30, 31,
            32, 34, 35, 36, 38, 39, 40, 42, 44, 46, 48,
            50, 52, 55, 58, 61, 64, 68, 72, 75, 80, 85,
            92, 101, 112, 127, 147, 168, 182, 194, 205,
        ),
    },
    64:{
        1:(
            1, 2, 2, 3, 4, 5, 7, 10, 13, 16, 19, 22, 24, 27,
            30, 32, 35, 38, 43, 48, 56, 78, 101, 120, 157,
        ),
        2:(
            1, 2, 2, 3, 4, 4, 6, 9, 12, 14, 17, 19, 21, 24,
            26, 28, 31, 33, 37, 42, 49, 68, 89, 105, 138,
        ),
        3:(
            1, 1, 2, 3, 3, 4, 5, 8, 10, 13, 15, 17, 19, 21,
            23, 25, 27, 30, 33, 37, 44, 60, 79, 93, 122,
        ),
        4:(
            7, 8, 8, 9, 9, 10, 11, 12, 13, 13, 14, 15, 16,
            16, 17, 18, 19, 19, 20, 21, 22, 24, 25, 27, 28,
            29, 30, 32, 33, 34, 35, 37, 39, 41, 43, 45, 48,
            50, 53, 56, 60, 64, 68, 74, 81, 89, 98, 109,
            122, 136, 146, 154, 162, 178, 220, 249,
        ),
        5:(
            1, 1, 1, 2, 2, 3, 4, 6, 7, 9, 10, 12, 13, 15,
            16, 17, 19, 21, 23, 26, 30, 42, 55, 65, 85,
        ),
        7:(
            5, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10,
            11, 11, 12, 13, 13, 14, 15, 16, 16, 17, 18,
            19, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29,
            31, 33, 35, 37, 39, 42, 46, 50, 54, 60, 67,
            75, 83, 90, 95, 100, 110, 135, 153, 172, 192,
        ),
    }
}


## Compensation data from datasheet

RxCompIndex = {
    16: {
        1: 1,
        2: 1,
        3: 1,
        4: 3,
        5: 1,
        7: 3,
    },
    64: {
        1: 2,
        2: 2,
        3: 2,
        4: 4,
        5: 2,
        7: 4,
    }
}

RxCompDataAdd = (
    # RSL, 16/500,64/500,16/900,64/900, 
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

RxCompData = (
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


RXC = np.array(RxCompData)

Xrx = 1.00 * RXC[:,0]
Yrx = 0.01 * RXC[:,RxCompIndex[Prf][Ch]]


##
## Functions
##

CompSplines = {
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
             ((-69.0, -61.0), (-95.74259549796217, -5.259534749105479, -0.05323809715869743)),
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


def XSpline(spline,X):
    for S in spline:
        if S[0][0] < X <= S[0][1]:
            Y = S[1][0] + S[1][1]*X + S[1][2]*X*X
            return Y
    raise ValueError


def DistComp(PWR,CH,PRF):
    if CH in (1,2,3,5):
        BW = 500
    elif CH in (4,7):
        BW = 900
    else:
        raise ValueError
    if PRF not in (16,64):
        raise ValueError
    try:
        Spl = CompSplines[BW][PRF]
        Cpl = XSpline(Spl,PWR)
        return -0.01 * Cpl
    except:
        return None



##
## Evaluation
##

B = OffsetBase[Prf][Ch]
D = OffsetData[Prf][Ch]
N = len(D)

X = np.zeros(N)
Y = np.zeros(N)
Z = np.zeros(N)

for i in range(N):
    X[i] = 0.25*D[i]
    Y[i] = DAI(X[i],Fc[Ch],Atten[Ch])
    Z[i] = 0.01 * (i + B)

XX = np.linspace(0.1,50,100)
AT = DAI(XX,Fc[Ch],Atten[Ch])


## Plotting

fig,ax = plot.subplots(2,2,figsize=(20,15),dpi=150)

fig.suptitle('Ch{}/PRF{}'.format(Ch,Prf))

ax[0,0].set_title('Distance compensation')
ax[0,0].set_xlabel('[m]')
ax[0,0].set_ylabel('[m]')

ax[0,0].plot(X,Z,'b*-')


ax[0,1].set_title('Rx Level compensation')
ax[0,1].set_xlabel('[dBm]')
ax[0,1].set_ylabel('[m]')

ax[0,1].plot(Xrx,Yrx,'ro-')


ax[1,0].set_title('Comparison')
ax[1,0].set_xlabel('[dBm]')
ax[1,0].set_ylabel('[m]')

Xpl = np.linspace(-100,-50,100)
Ypl = np.zeros(100)
for i in range(100):
    Ypl[i] = DistComp(Xpl[i],Ch,Prf)

ax[1,0].plot(Y,Z,'b*-')
ax[1,0].plot(Xrx, Yrx, 'r.')
ax[1,0].plot(Xpl, Ypl, 'y-')
    
ax[1,1].set_title('Ch{} Propagation'.format(Ch,Prf))
ax[1,1].set_xlabel('[m]')
ax[1,1].set_ylabel('[dBm]')

ax[1,1].plot(XX,AT,'m-')


#plot.show()


##
## Error effect (antenna delay, scaling, etc.)
##

ANTD = ( 0.00, 0.25, 0.50, 0.75, 1.00 )

SCALE = ( 1.00, 1.10, 1.20, 1.30, 1.40 )

N = 100

XX = np.linspace(0.10, 50.0, N)
YY = np.zeros(N)
ZZ = np.zeros(N)

fig,ax = plot.subplots(2,2,figsize=(20,15),dpi=150)

fig.suptitle('Error effects Ch{}/PRF{}'.format(Ch,Prf))

ax[0,0].set_title('Order-0 error @ Propagation model')
ax[0,0].set_xlabel('[m]')
ax[0,0].set_ylabel('[dBm]')

for d in ANTD:
    YY = DAI(XX+d, Fc[Ch], Atten[Ch])
    ax[0,0].plot(XX,YY)

    
ax[0,1].set_title('Order-0 error @ compensation model')
ax[0,1].set_xlabel('[m]')
ax[0,1].set_ylabel('[m]')

#ax[0,1].set_xlim([0,10])
ax[0,1].set_ylim([-0.6,0.6])

ax[0,1].plot(X,Z,'b*-')

for d in ANTD:
    for i in range(N):
        YY[i] = DAI(XX[i]+d, Fc[Ch], Atten[Ch])
        ZZ[i] = DistComp(YY[i], Ch, Prf)
    ax[0,1].plot(XX,ZZ,'-')


ax[1,0].set_title('Order-1 error @ Propagation model')
ax[1,0].set_xlabel('[m]')
ax[1,0].set_ylabel('[dBm]')

for s in SCALE:
    YY = DAI(s*XX, Fc[Ch], Atten[Ch])
    ax[1,0].plot(XX,YY)


ax[1,1].set_title('Order-1 error @ compensation model')
ax[1,1].set_xlabel('[m]')
ax[1,1].set_ylabel('[m]')

#ax[1,1].set_xlim([0,10])
ax[1,1].set_ylim([-0.6,0.6])

ax[1,1].plot(X,Z,'b*-')

for s in SCALE:
    for i in range(N):
        YY[i] = DAI(s*XX[i], Fc[Ch], Atten[Ch])
        ZZ[i] = DistComp(YY[i], Ch, Prf)
    ax[1,1].plot(XX,ZZ,'-')




plot.show()

