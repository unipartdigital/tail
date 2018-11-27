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
Fc = ( 3494.4, 3993.6, 4492,8, 3993.6, 6489.6, None, 6489.6 )

Cc = 4*Pi/Cs

DAI = lambda m,fc,pt: pt - 20*np.log10(m*Cc*fc*1e6)
ADI = lambda dBm,fc,pt: 10**((pt-dBm)/20)/(Cc*fc*1e6)


X = np.linspace(1,100,1000)
Y = DAI(X,Fc[Ch],Pt)

YY = np.linspace(np.min(Y),np.max(Y),1000)
XX = ADI(YY,Fc[Ch],Pt)


fig,ax = plot.subplots(1,1,figsize=(10,10),dpi=80)

ax.set_title('Ch{}'.format(Ch))
ax.set_ylabel('[dBm]')
ax.set_xlabel('[m]')
ax.grid(True)

ax.plot(X,Y-20,'-')
ax.plot(X,Y-10,'-')
ax.plot(X,Y,'-')
ax.plot(X,Y+10,'-')
ax.plot(X,Y+20,'-')

ax.plot(XX,YY,'-')


plot.show()

