#!/usr/bin/python3

import sys
import time
import math
import json
import argparse
import pprint
import csv
import gzip


def main():

    parser = argparse.ArgumentParser(description="Data collector")
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-o', '--output', type=str, default=None)
    parser.add_argument('-d', '--distance', type=float, default=0.0)
    parser.add_argument('-p', '--prefix', type=str, default='test')
    parser.add_argument('dir', type=str, default='.')
    
    args = parser.parse_args()

    dst = gzip.open(args.output, 'wt+')

    start = 0
    
    for power in range(0,239):

        file  = args.dir + '/'
        file += '{}-{:.2f}m-0x{:02x}.csv.gz'.format(args.prefix,args.distance,power)
        
        src = gzip.open(file,'rt')
        CSV = csv.reader(src, delimiter=',')
        
        for row in CSV:
            id = int(row[0],0)
            row[0]  = '0x{:08x}'.format(id + start)
            row[23] = '{:.3f}'.format(args.distance)
            out  = ','.join(row)
            if args.verbose > 0:
                print(out)
            dst.write(out + '\n')

        start = id + 1
        
        src.close()

    dst.close()
        
if __name__ == "__main__": main()

