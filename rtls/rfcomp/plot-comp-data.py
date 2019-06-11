#!/usr/bin/python3

import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot
import scipy.interpolate as interp

from pprint import pprint

SavePath = ''


RxCorrData = (
    # RSL, 16/500,64/500,16/900,64/900, 
    (-95,  11.5,   8.5,  39.4,  28.4),
    (-93,  11.0,   8.1,  35.6,  26.4),
    (-91,  10.6,   7.6,  33.9,  24.5),
    (-89,   9.7,   7.1,  32.1,  23.3),
    (-87,   8.4,   6.2,  29.4,  19.7),
    (-85,   6.5,   4.9,  25.4,  17.5),
    (-83,   3.6,   4.2,  21.0,  15.3),
    (-81,   0.0,   3.5,  15.8,  12.7),
    (-79,  -3.1,   2.1,   9.7,   9.1),
    (-77,  -5.9,   0.0,   4.2,   4.9),
    (-75,  -8.4,  -2.7,   0.0,   0.0),
    (-73, -10.9,  -5.1,  -5.1,  -5.8),
    (-71, -12.7,  -6.9,  -9.5, -10.0),
    (-69, -14.3,  -8.2, -13.8, -15.0),
    (-67, -16.3,  -9.3, -17.6, -19.9),
    (-65, -17.9, -10.0, -21.0, -23.5),
    (-63, -18.7, -10.5, -24.4, -26.6),
    (-61, -19.8, -11.0, -27.5, -29.5),
)


C = np.array(RxCorrData)

XC = C[:,0] + 0.0

C1 = 0.0 - C[:,1]
C2 = 0.0 - C[:,2]
C3 = 0.0 - C[:,3]
C4 = 0.0 - C[:,4]


fig,ax = plot.subplots(1,1,figsize=(20,15),dpi=150)

#fig.tight_layout()

ax.set_title('6.5GHz/500MHz/PRF16')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[m]')
ax.set_xlim([-120,-40])
ax.set_ylim([-40,40])
ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-40,40,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-40,40,2), minor=True )
ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)
ax.plot(XC,C1)

fig.savefig(SavePath + 'rxcomp-500MHz-PRF16.png')


fig,ax = plot.subplots(1,1,figsize=(20,15),dpi=150)

#fig.tight_layout()

ax.set_title('6.5GHz/500MHz/PRF64')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[m]')
ax.set_xlim([-120,-40])
ax.set_ylim([-20,20])
ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-20,20,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-20,20,1), minor=True )
ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)
ax.plot(XC,C2)

fig.savefig(SavePath + 'rxcomp-500MHz-PRF64.png')


fig,ax = plot.subplots(1,1,figsize=(20,15),dpi=150)

#fig.tight_layout()

ax.set_title('6.5GHz/900MHz/PRF16')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[m]')
ax.set_xlim([-120,-40])
ax.set_ylim([-80,80])
ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-80,80,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-80,80,2), minor=True )
ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)
ax.plot(XC,C3)

fig.savefig(SavePath + 'rxcomp-900MHz-PRF16.png')


fig,ax = plot.subplots(1,1,figsize=(20,15),dpi=150)

#fig.tight_layout()

ax.set_title('6.5GHz/900MHz/PRF64')
ax.set_xlabel('[dBm]')
ax.set_ylabel('[m]')
ax.set_xlim([-120,-40])
ax.set_ylim([-60,60])
ax.set_xticks( np.arange(-120,-40,10) )
ax.set_yticks( np.arange(-60,60,10) )
ax.set_xticks( np.arange(-120,-40,1), minor=True )
ax.set_yticks( np.arange(-60,60,2), minor=True )
ax.grid(which='both')
ax.grid(which='minor', alpha=0.2)
ax.grid(which='major', alpha=0.5)
ax.plot(XC,C4)

fig.savefig(SavePath + 'rxcomp-900MHz-PRF64.png')


plot.show()
