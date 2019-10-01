#!/usr/bin/env python3

from scipy.optimize import least_squares

measurements = [
    (1,  2,  338),
    (1,  3,  351),
    (1,  4,  800),
    (1,  5, 1030),
    (1,  6,  507),
    (1,  7,  632),
    (1,  8,  804),
    (1,  9,  800),
    (1, 10, 1075),
    (2,  3,   91),
    (2,  4,  463),
    (2,  5,  712),
    (2,  6,  542),
    (2,  7,  644),
    (2,  8,  667),
    (2,  9,  583),
    (2, 10,  774),
    (3,  4,  472),
    (3,  5,  705),
    (3,  6,  535),
    (3,  7,  650),
    (3,  8,  660),
    (3,  9,  590),
    (3, 10,  779),
    (4,  5,  325),
    (4,  6,  834),
    (4,  7,  883),
    (4,  8,  715),
#    (4,  9,  351),
    (4, 10,  440),
    (5,  6,  903),
    (5,  7,  917),
    (5,  8,  646),
    (5,  9,  460),
    (5, 10,  176),
    (6,  7,  162),
    (6,  8,  388),
    (6,  9,  507),
    (6, 10,  882),
    (7,  9,  476),
    (7, 10,  865),
#    (8,  9,  316),
    (8, 10,  577),
    (9, 10,  388),
]

nanchors = 10

zmeasurements = [
     32.0,
     33.0,
    124.2,
     31.5,
    124.4,
    124.2,
     30.0,
    120.5,
     33.8,
     32.5,
]

# This takes a list of nanchors*2 values corresponding to
# x1..n and y1..n
def f(X):
    result = []
    for pair in measurements:
        (anchor1, anchor2, distance) = pair
        x1 = X[anchor1-1]
        x2 = X[anchor2-1]
        y1 = X[anchor1-1 + nanchors]
        y2 = X[anchor2-1 + nanchors]
        z1 = -zmeasurements[anchor1-1]
        z2 = -zmeasurements[anchor2-1]
        result.append((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2 - distance**2)
    # Determine set of axes by fixing an anchor as the origin
    result.append(X[9-1])
    result.append(X[nanchors+9-1])
    # And the second anchor on the X axis
    result.append(X[nanchors+10-1])
    return result

#initial = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#initial = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
initial = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 100, 100, 100, 100, 6, 7, 8, 9, 10]

print(f(initial))

print(least_squares(f, initial, ftol=0, xtol=1e-15))
