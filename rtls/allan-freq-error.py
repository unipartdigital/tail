#!/usr/bin/python3
#
# Analyse the frequence error between two anchors.
#

import argparse
import socket
import pprint
import math
import tail
import sys
import csv

import matplotlib.pyplot as plt


verbose = 0


def getAncCol(data,index,inc):
    if index in data:
        for i in range(0,4):
            col = 2+2*i+inc
            if data[index][col] != '':
                return col
    raise ValueError


def getData(data,index,col):
    if index in data:
        return data[index][col]
    raise ValueError

def getTime(data,index):
    return float(getData(data,index,1))

def getTS(data,index,col):
    ts = int(getData(data,index,col))
    if ts == 0:
        raise ValueError
    return ts


def Allan(data,cols,first,last,skip):
    
    FAILS = 0

    TmCNT = 0
    TmSUM = 0.0
    AlCNT = 0
    AlSUM = 0.0
    AlMAX = 0.0
    CrNUM = 0.0
    CrDEN = 0.0
    CrOLD = None

    C1 = cols[0]
    C2 = cols[1]

    if verbose:
        print('Analysing [{},{}] with skip:{}'.format(first,last,skip))
    
    for i in range(first,last,skip):
        
        if i in data:

            try:
                
                T1 = getTime(data,i)
                T2 = getTime(data,i+skip)

                T21 = T2 - T1

                J1 = getTS(data,i,C1)
                J2 = getTS(data,i+skip,C1)
                J3 = getTS(data,i,C2)
                J4 = getTS(data,i+skip,C2)

                J21 = J2 - J1
                J43 = J4 - J3
                
                Er = J43 - J21
                Cr = Er / J21

                if verbose:
                    print('{}: {:.6f} {:.6f} {:.6f}ppm'.format(i,T2,T21,Cr*1E6))
                    
                if math.fabs(Cr) < 1E-4:

                    TmCNT += 1
                    TmSUM += T21
                    
                    CrNUM += Er
                    CrDEN += J21
                    
                    if CrOLD is not None:
                        DELTA = math.fabs(Cr-CrOLD)
                        if DELTA > AlMAX:
                            AlMAX = DELTA
                        AlCNT += 1
                        AlSUM += DELTA*DELTA

                    CrOLD = Cr
                                
                else:
                    raise ValueError
                    
            except:
                FAILS += 1

    
    TmAVG = TmSUM/TmCNT
    CrAVG = CrNUM/CrDEN
    AlVAR = AlSUM/AlCNT
    AlDEV = math.sqrt(0.5*AlVAR)

    return (TmAVG,CrAVG,AlDEV,AlMAX,FAILS)
    



def main():

    global verbose
    
    parser = argparse.ArgumentParser(description="Frequency analyser")

    parser.add_argument('-c', '--columns', type=str, default=None)
    parser.add_argument('-s', '--skip', type=int, default=1)
    parser.add_argument('-r', '--resolution', type=float, default=None)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('file', type=str, help="Data file")
    
    args = parser.parse_args()

    verbose = args.verbose

    if args.columns is not None:
        cols = [ int(col) for col in args.columns.split(',') ]
    else:
        cols = [ 2, 5 ]

    print('Using colums {}'.format(cols))


    ##
    ## Read data file
    ##
    
    data = {}

    index = 0
    count = 0
    
    with open(args.file) as csvfile:
        CSV = csv.reader(csvfile, delimiter=',')
        for row in CSV:
            count += 1
            index = int(row[0])
            data[index] = row


    ##
    ## Analysis
    ##

    if args.resolution is not None:
    
        ranges = [ 1 ]
        mult = 10**(1/args.resolution)
        skip = 1.0
        while skip < index/10:
            skip *= mult
            if int(skip) != ranges[-1]:
                ranges.append(int(skip))

        Xx = []
        Yy = []
        
        for skip in ranges:
            (TmAVG,CrAVG,AlDEV,AlMAX,fails) = Allan(data,cols,1,index,skip)
            Xx.append(TmAVG)
            Yy.append(AlDEV)
            
            print('Period {:.3f}ms Error:{:.6f}ppm Allan.dev:{:.6f} Allan.max:{:.6f} fail:{:.1f}% [{}] '.format(TmAVG*1E3,CrAVG*1E6,AlDEV*1E6,AlMAX*1E6,100*fails/count,fails))

        fg,ax = plt.subplots(figsize=(12,10))
        ax.set_title('Allan Deviation')
        ax.loglog(Xx,Yy,'k.-')
        
        plt.show()
        
    else:
        
        (TmAVG,CrAVG,AlDEV,AlMAX,fails) = Allan(data,cols,1,index,args.skip)
        print('Period {:.3f}ms Error:{:.6f}ppm Allan.dev:{:.6f} Allan.max:{:.6f} fail:{:.1f}% [{}] '.format(TmAVG*1E3,CrAVG*1E6,AlDEV*1E6,AlMAX*1E6,100*fails/count,fails))


        
if __name__ == "__main__":
    main()

