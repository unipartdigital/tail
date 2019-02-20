#!/usr/bin/python3


# Example usage:
#
# inst = TF930.open_serial('/dev/ttyUSB0', 115200, timeout=15)
# print(inst.name)
# inst.set(inst.Coupling.ac)
# inst.set(inst.Attenuation.atten_5to1)
# inst.set(inst.Impedance.imp_1m)
# inst.set(inst.Edge.rising)
# inst.set(inst.LowPass.lpf_out)
# inst.set(inst.MeasurementTime.t_1s)
# inst.threshold_offset = 0
# inst.mode = inst.Mode.a_frequency
# print(inst.measure())


import instruments
from instruments.abstract_instruments import Instrument

from enum import Enum
import quantities as pq
from quantities import Quantity
import re
import time

class TF930(Instrument):
    def __init__(self, *args):
        self.mode_cached = None
        super().__init__(*args)

    class Mode(Enum):
        a_period = 'F1'
        b_period = 'F0'
        a_frequency = 'F2'
        b_frequency = 'F3'
        ratio_ba = 'F4'
        a_width_high = 'F5'
        a_width_low = 'F6'
        a_count = 'F7'
        a_ratio_hl = 'F8'
        a_duty_cycle = 'F9'

    class Impedance(Enum):
        imp_1m = 'Z1'
        imp_50ohm = 'Z5'

    class Attenuation(Enum):
        atten_1to1 = 'A1'
        atten_5to1 = 'A5'

    class Coupling(Enum):
        ac = 'AC'
        dc = 'DC'

    class Edge(Enum):
        rising = 'ER'
        falling = 'EF'

    class LowPass(Enum):
        lpf_in = 'FI'
        lpf_out = 'FO'

    class MeasurementTime(Enum):
        t_300ms = 'M1'
        t_1s    = 'M2'
        t_10s   = 'M3'
        t_100s  = 'M4'

    def sendcmd(self, command):
        super().sendcmd(command)
        time.sleep(0.1)
        #super().query('I?')

    def set(self, setting):
        if isinstance(setting, Enum):
            setting = setting.value
        self.sendcmd(setting)

    def local(self):
        self.sendcmd('LOCAL')

    def stop(self):
        self.sendcmd('STOP')

    @property
    def name(self):
        return self.query('*IDN?')

    @property
    def mode(self):
        return self.mode_cached

    @mode.setter
    def mode(self, mode):
        self.mode_cached = mode
        self.set(mode)

    @property
    def threshold(self):
        value = self.query('TT?')
        match = re.search("([\d+-]+)mV", value)
        if match:
            return float(match.group(1)) * pq.mV

    @threshold.setter
    def threshold(self, value):
        if isinstance(value, Quantity):
            value.units = pq.mV
            value = float(value)
        if (value < -300):
            raise Exception("Threshold is too low")
        if (value > 2100):
            raise Exception("Threshold is too high")
        self.sendcmd('TT ' + str(round(value)))

    @property
    def threshold_offset(self):
        value = self.query('TO?')
        match = re.search("([\d+-]+)mV", value)
        if match:
            return float(match.group(1)) * pq.mV

    @threshold_offset.setter
    def threshold_offset(self, value):
        if isinstance(value, Quantity):
            value.units = pq.mV
            value = float(value)
        if (value < -60):
            raise Exception("Threshold offset is too low")
        if (value > 60):
            raise Exception("Threshold offset is too high")
        self.sendcmd('TO ' + str(round(value)))

    def threshold_auto(self):
        self.sendcmd('TA')

    def parse(self, value):
        match = re.search("([0-9.]+)e([+-][0-9])(..)", value)
        if match:
            mantissa = match.group(1)
            exponent = match.group(2)
            units = match.group(3)
            result = float(mantissa + 'e' + exponent)
            if units == 'Hz':
                result = result * pq.Hz
            if units == 's ':
                result = result * pq.s
            if units == '% ':
                result = result / 100
            return result
        raise Exception("Invalid result")

    def measure(self, mode=None):
        if mode != None:
            self.mode = mode
        else:
            mode = self.mode
        if mode == None:
            raise Exception("Can't measure without setting mode")
        value = self.query('N?')
        return self.parse(value)

    # Things that could still be implemented:
    # status
    # Measuring in ways other than taking the next reading

