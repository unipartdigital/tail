#!/usr/bin/python3


import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot
import scipy.interpolate as interp

from pprint import pprint


RxPowerData = (
    (0, 0, 0, 0),
    (25, 25, 25, 25),
    (65, 65, 65, 65),
    (105, 105, 105, 105),
    (145, 145, 145, 145),
    (185, 185, 185, 185),
    (225, 225, 225, 225),
    (265, 265, 265, 265),
    (305, 305, 303, 305),
    (345, 345, 342, 345),
    (385, 385, 382, 385),
    (425, 420, 422, 425),
    (465, 460, 466, 465),
    (505, 502, 506, 505),
    (545, 542, 546, 545),
    (585, 576, 578, 576),
    (625, 612, 606, 622),
    (665, 644, 630, 658),
    (705, 668, 670, 695),
    (745, 686, 706, 730),
    (785, 710, 738, 765),
    (825, 716, 774, 795),
    (865, 735, 802, 810),
    (905, 752, 846, 840),
    (945, 763, 878, 865),
    (985, 775, 898, 888),
    (1025, 784, 921, 908),
    (1065, 796, 938, 928),
    (1105, 808, 954, 948),
    (1145, 816, 961, 966),
    (1185, 831, 975, 980),
    (1225, 843, 986, 1004),
    (1265, 854, 990, 1024),
    (1305, 866, 997, 1050),
    (1345, 883, 1006, 1070),
    (1385, 895, 1010, 1086),
    (1425, 904, 1018, 1098),
    (1465, 915, 1022, 1110),
    (1505, 924, 1026, 1118),
    (1545, 934, 1030, 1128),
    (1585, 944, 1034, 1140),
)

D = np.array(RxPowerData)

X  = D[:,0] / 40
Y1 = D[:,1] / 40
Y2 = D[:,2] / 40
Y3 = D[:,3] / 40

pprint(X)
pprint(Y1)
pprint(Y2)

BY1 = interp.LSQUnivariateSpline(X,Y1,[10,20])
YY1 = BY1(X)
BX1 = interp.LSQUnivariateSpline(Y1,X,[10,20])
XX1 = BX1(Y1)

BY2 = interp.LSQUnivariateSpline(X,Y2,[10,25])
YY2 = BY2(X)
BX2 = interp.LSQUnivariateSpline(Y2,X,[10,22.5])
XX2 = BX2(Y2)

BY3 = interp.LSQUnivariateSpline(X,Y3,[10,25])
YY3 = BY3(X)
BX3 = interp.LSQUnivariateSpline(Y3,X,[10,22.5])
XX3 = BX3(Y3)


print('1: Max X->Y error: {}'.format(max(abs(Y1-YY1))))
print('1: Max Y->X error: {}'.format(max(abs(X-XX1))))

print('2: Max X->Y error: {}'.format(max(abs(Y2-YY2))))
print('2: Max Y->X error: {}'.format(max(abs(X-XX2))))

print('3: Max X->Y error: {}'.format(max(abs(Y3-YY3))))
print('3: Max Y->X error: {}'.format(max(abs(X-XX3))))


fig,ax = plot.subplots(2,2,figsize=(15,15),dpi=80)

ax[0,0].set_title('RF Power Conversion Data')
ax[0,0].set_xlabel('[dBm]')
ax[0,0].set_ylabel('[dBm]')
ax[0,0].grid(True)

ax[0,0].plot(X,X)
ax[0,0].plot(X,Y1,'.-')
ax[0,0].plot(X,Y2,'.-')
ax[0,0].plot(X,Y3,'.-')


ax[0,1].set_title('RF Power Conversion PRF16')
ax[0,1].set_xlabel('[dBm]')
ax[0,1].set_ylabel('[dBm]')
ax[0,1].grid(True)

ax[0,1].plot(X,X)
ax[0,1].plot(X,Y1)
ax[0,1].plot(X,YY1)
ax[0,1].plot(X,Y1-YY1)
ax[0,1].plot(Y1,X)
ax[0,1].plot(Y1,XX1)
ax[0,1].plot(XX1-X,X)


ax[1,0].set_title('RF Power Conversion PRF64 Open Space')
ax[1,0].set_xlabel('[dBm]')
ax[1,0].set_ylabel('[dBm]')
ax[1,0].grid(True)

ax[1,0].plot(X,X)
ax[1,0].plot(X,Y2)
ax[1,0].plot(X,YY2)
ax[1,0].plot(X,Y2-YY2)
ax[1,0].plot(Y2,X)
ax[1,0].plot(Y2,XX2)
ax[1,0].plot(XX2-X,X)


ax[1,1].set_title('RF Power Conversion PRF64 Multipath')
ax[1,1].set_xlabel('[dBm]')
ax[1,1].set_ylabel('[dBm]')
ax[1,1].grid(True)

ax[1,1].plot(X,X)
ax[1,1].plot(X,Y3)
ax[1,1].plot(X,YY3)
ax[1,1].plot(X,Y3-YY3)
ax[1,1].plot(Y3,X)
ax[1,1].plot(Y3,XX3)
ax[1,1].plot(XX3-X,X)


plot.show()

