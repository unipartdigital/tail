#!/usr/bin/python3

import sys
import time
import math
import pprint
import csv
import gzip


Cabs = 299792458
Cair = 299705000

DW1000_CLOCK_GHZ = 63.8976
DW1000_CLOCK_HZ  = DW1000_CLOCK_GHZ * 1E9


class Record():

    def __init__(self,row):
        self.bid = int(row[0],0)
        self.eui = str(row[1])
        self.time_sw = int(row[2],0)
        self.time_hires = int(row[3],0)
        self.time_raw = int(row[4],0)
        self.rxpower = float(row[5])
        self.fppower = float(row[6])
        self.clock_ratio = float(row[7])
        self.lqi = int(row[8],0)
        self.snr = int(row[9],0)
        self.fpr = int(row[10],0)
        self.noise = int(row[11],0)
        self.rxpacc = int(row[12],0)
        self.fp_index = int(row[13],0)
        self.fp_ampl1 = int(row[14],0)
        self.fp_ampl2 = int(row[15],0)
        self.fp_ampl3 = int(row[16],0)
        self.cir_pwr = int(row[17],0)
        self.fp_pwr = int(row[18],0)
        self.ttcko = int(row[19],0)
        self.ttcki = int(row[20],0)
        self.temp = float(row[21])
        self.volt = float(row[22])

        if self.time_sw:
            self.time = self.time_sw >> 32
        else:
            self.time = None


    def __iter__(self):
        return ((key,val) for (key,val) in self.__dict__.items())

    def __str__(self):
        ret = 'Record:\n'
        for (key,val) in self:
            ret += '{:20s} : {}\n'.format(key,val)
        return ret

    def isTx(self):
        return (self.lqi == 0)

    def txPower(self):
        if self.isTx():
            return self.cir_pwr
        else:
            return None

    def check(self, pair):
        if pair is None:
            return True
        if self.isTx():
            if pair[0] == self.eui:
                return True
        else:
            if pair[1] == self.eui:
                return True
        return False
        
    def checkEUIs(self, pairs):
        if pairs is None:
            return True
        for pair in pairs:
            if self.check(pair):
                return True
        return False


class Blink():

    def __init__(self,bid):
        self.time = None
        self.bid = bid
        self.rx = {}
        self.tx = {}

    def __iter__(self):
        return ((key,val) for (key,val) in self.rx.items())

    def __str__(self):
        ret = 'Blink ID:{} Time:{}\n'.format(self.bid,self.time)
        for (key,rec) in self.tx.items():
            ret += str(rec)
        for (key,rec) in self.rx.items():
            ret += str(rec)
        return ret

    def add(self,rec):
        if rec.isTx():
            self.tx[rec.eui] = rec
        else:
            self.rx[rec.eui] = rec
            if self.time is None or self.time > rec.time:
                self.time = rec.time
    
    def get(self,eui):
        if eui in self.tx:
            return self.tx[eui]
        if eui in self.rx:
            return self.rx[eui]
        return None

    def getTx(self,eui):
        if eui in self.tx:
            return self.tx[eui]
        return None
    
    def getRx(self,eui):
        if eui in self.rx:
            return self.rx[eui]
        return None

    def check(self, pair):
        if pair is None:
            return True
        return pair[0] in self.tx and pair[1] in self.rx

    def checkEUIs(self, pairs):
        if pairs is None:
            return True
        for pair in pairs:
            if self.check(pair):
                return True
        return False
    


class BlinkStorm():

    def __init__(self):
        self.blk = {}
        self.start = 0
        self.minid = None
        self.maxid = None
        
    def __iter__(self):
        return ((key,val) for (key,val) in self.blk.items())

    def add(self, blk):
        self.blk[blk.bid] = blk

    def rem(self, bid):
        del self.blk[bid]

    def get(self,bid):
        return self.blk[bid]

    def load(self, file, EUIs=None):
        blk = Blink(0)
        if file.endswith('.gz'):
            input = gzip.open(file,'rt')
        else:
            input = open(file)
        CSV = csv.reader(input, delimiter=',')
        for row in CSV:
            rec = Record(row)
            if rec.bid != blk.bid:
                if blk.checkEUIs(EUIs):
                    self.add(blk)
                blk = Blink(rec.bid)
            if rec.checkEUIs(EUIs):
                blk.add(rec)
        input.close()
        self.normalise()

    def normalise(self):
        for id in list(self.blk):
            blk = self.get(id)
            if not blk.tx or blk.time is None:
                self.rem(id)
        self.minid = min(self.blk.keys())
        self.maxid = max(self.blk.keys())
        self.start = self.blk[self.minid].time
        for blk in self.blk.values():
            blk.time -= self.start
            for rec in blk.rx.values():
                rec.time -= self.start

    def linsearch_fwd(self, index, EUIs=None, limit=100):
        while index <= self.maxid and limit > 0:
            if index in self.blk and \
               self.blk[index].checkEUIs(EUIs):
                return index
            index += 1
            limit -= 1
        return None
    
    def linsearch_bwd(self, index, EUIs=None, limit=100):
        while index >= self.minid and limit > 0:
            if index in self.blk and \
               self.blk[index].checkEUIs(EUIs):
                return index
            index -= 1
            limit -= 1
        return None
    
    def search(self, time, EUIs=None, limit=32):
        start = self.linsearch_fwd(self.minid, EUIs)
        end   = self.linsearch_bwd(self.maxid, EUIs)
        while limit > 0:
            index = self.linsearch_fwd((start+end)//2, EUIs)
            if index == start or index == end:
                return index
            x = self.get(index)
            if time <= x.time:
                end = index
            else:
                start = index
            limit -= 1
        return None


