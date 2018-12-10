#!/usr/bin/python3
#
# Standard propagation model for RF signals
#

import sys
import math

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot


Ch = 5
Pt = 0

Pi = math.pi
Cs = 299792458
Cc = 4*Pi/Cs
Fc = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )

DAI = lambda m,fc,pt: pt - 20*np.log10(m*Cc*fc*1e6)
ADI = lambda dBm,fc,pt: 10**((pt-dBm)/20)/(Cc*fc*1e6)


X = np.linspace(1,100,100)

Ya = DAI(X,Fc[Ch],Pt-10)
Yb = DAI(X,Fc[Ch],Pt)
Yc = DAI(X,Fc[Ch],Pt+10)

YY = np.linspace(np.min(Yb),np.max(Yb),100)
XX = ADI(YY,Fc[Ch],Pt)


fig,ax = plot.subplots(1,2,figsize=(20,10),dpi=120)

ax[0].set_title('Ch{}'.format(Ch))
ax[0].set_ylabel('[dBm]')
ax[0].set_xlabel('[m]')
ax[0].grid(True)

ax[0].plot(X,Ya,'-')
ax[0].plot(X,Yb,'-')
ax[0].plot(X,Yc,'-')

ax[0].plot(XX,YY,'-')


Ya = DAI(X,Fc[1],Pt)
Yb = DAI(X,Fc[2],Pt)
Yc = DAI(X,Fc[3],Pt)
Yd = DAI(X,Fc[4],Pt)
Ye = DAI(X,Fc[5],Pt)
Yf = DAI(X,Fc[7],Pt)

ax[1].set_title('Channels 1-7')
ax[1].set_ylabel('[dBm]')
ax[1].set_xlabel('[m]')
ax[1].grid(True)

ax[1].plot(X,Ya,'-')
ax[1].plot(X,Yb,'-')
ax[1].plot(X,Yc,'-')
ax[1].plot(X,Yd,'-')
ax[1].plot(X,Ye,'-')
ax[1].plot(X,Yf,'-')


plot.show()

