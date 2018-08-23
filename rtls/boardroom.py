#!/usr/bin/python3
#
# Distance to coordinates converter for Tail algorithm development
#

import time
import math
import random


DELTA = 0.20

DIST = [
    [ 0.000, 8.395, 9.963, 5.385, 2.700, 6.200, 8.310, 6.170 ],
    [  None, 0.000, 5.390, 9.980, 6.035, 2.630, 6.340, 8.550 ],
    [  None,  None, 0.000, 8.390, 8.260, 6.215, 2.780, 6.390 ],
    [  None,  None,  None, 0.000, 6.310, 8.390, 6.060, 2.480 ],
    [  None,  None,  None,  None, 0.000, 3.418, 6.891, 5.955 ],
    [  None,  None,  None,  None,  None, 0.000, 5.958, 7.130 ],
    [  None,  None,  None,  None,  None,  None, 0.000, 3.800 ],
    [  None,  None,  None,  None,  None,  None,  None, 0.000 ],
]

FIXED = (
    (  True,  True,  True ),
    ( False,  True,  True ),
    ( False, False,  True ),
    (  True, False,  True ),
    ( False,  True,  True ),
    ( False,  True,  True ),
    ( False, False,  True ),
    ( False, False,  True ),
)

COORD = [
    [ 0.150, 0.475, 0.035 ],
    [ 8.540, 0.420, 0.035 ],
    [ 8.565, 5.810, 0.035 ],
    [ 0.175, 5.860, 0.035 ],
    [ 2.630, 0.185, 1.255 ],
    [ 6.220, 0.185, 1.255 ],
    [ 6.110, 6.150, 1.265 ],
    [ 2.315, 6.150, 1.270 ], 
]


def dist(x,y):
    return math.sqrt((x[0]-y[0])*(x[0]-y[0]) + (x[1]-y[1])*(x[1]-y[1]) + (x[2]-y[2])*(x[2]-y[2]))

def norm(x):
    return math.sqrt(x[0]*x[0] + x[1]*x[1] + x[2]*x[2])


def main():
    
    for i in range(1,8):
        for j in range(0,i):
            DIST[i][j] = DIST[j][i]

    for n in range(1000):
        for i in range(0,8):
            for j in range(0,8):
                if i != j:
                    Dij = DIST[i][j]
                    Cij = dist(COORD[i],COORD[j])
                    Err = Cij - Dij
                    for k in range(0,3):
                        Nor = (COORD[i][k] - COORD[j][k]) / Cij
                        Cor = DELTA * Err * Nor
                        if not FIXED[i][k]:
                            COORD[i][k] -= Cor
        print('======================================')
        for i in range(0,8):
            print('Anchor #{0} coord [{1[0]:.3f}, {1[1]:.3f}, {1[2]:.3f}]'.format(i+1,COORD[i]))
        time.sleep(0.05)
    

if __name__ == "__main__":
    main()

