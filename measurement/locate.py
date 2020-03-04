#!/usr/bin/env python3

from scipy.optimize import least_squares
import json

configfile = 'config.json'

with open(configfile) as file:
    config = json.load(file)

z = input("Z coordinate: ")

measurements = []
for anchor in config['ANCHORS']:
    s = input("Anchor {}: ".format(anchor['name']))
    if (s):
        coords = anchor['coord']
        measurements.append((coords, float(s), float(z)))

totals = (0, 0, 0)
count = 0
for m in measurements:
    (coords, distance, z1) = m
    (x, y, z) = coords
    (xt, yt, zt) = totals
    totals = (xt + x, yt + y, zt + z)
    count = count + 1

(xt, yt, zt) = totals
average = (xt / count, yt / count, zt / count)

# X is [x, y]
def f(X):
    result = []
    for m in measurements:
        (coords, distance, z1) = m
        x1 = X[0]
        y1 = X[1]
        (x2, y2, z2) = coords
        result.append((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2 - distance**2)
    return result

(xa, ya, za) = average
initial = [xa, ya]

print(f(initial))

print(least_squares(f, initial, ftol=0, xtol=1e-15))
