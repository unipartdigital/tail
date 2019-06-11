#!/usr/bin/python3

x = 100
x = bytes((10,11,12))
y = bytes(reversed(tuple(x)))

print('type:{} data:{}'.format(type(y),y))

