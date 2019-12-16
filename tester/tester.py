#!/usr/bin/python3

import kivy
kivy.require('1.10.1')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import ObjectProperty
from kivy.clock import Clock

import os
from os.path import expanduser, join
import subprocess
import sys

import threading
import time
import json
import configparser
import netaddr
import traceback
import struct

import tf930
import instruments

import serial
import spidev

from pihat.eeprom import EepromDevice, EepromValueError, EepromDescription, EepromVerificationError
from fdt import parse_dtb

config = configparser.ConfigParser()
config.read('tester.ini')

real_hardware = config.getboolean('Tester', 'RealHardware', fallback=True)
firmware_directory = expanduser(config.get('Tester', 'FirmwareDirectory', fallback='~/firmware'))
production_firmware = config.get('Tester', 'ProductionFirmware', fallback='production.hex')
flash_command = config.get('Tester', 'FlashCommand', fallback='./flash.sh')

device_frequencycounter = config.get('Tester', 'FrequencyCounter', fallback='')
device_multimeter = config.get('Tester', 'Multimeter', fallback='')
device_gpsdo = config.get('Tester', 'GPSDO', fallback='')
device_dut = config.get('Tester', 'DUT', fallback='/dev/ttyS0')

eui_file = expanduser(config.get('Tester', 'EUIFile', fallback='~/eui'))
results_file = expanduser(config.get('Tester', 'ResultsFile', fallback='~/test-results.txt'))
config_file = expanduser(config.get('Tester', 'ConfigFile', fallback='~/tag-config.txt'))
eeprom_yaml = expanduser(config.get('Tester', 'EepromYaml', fallback='~/hat-eeprom.yaml'))
eeprom_dts = expanduser(config.get('Tester', 'EepromDts', fallback='~/hat-eeprom.dts'))

limit_precondition = config.get('Limits', 'Precondition', fallback='50')
limit_charge = config.get('Limits', 'Charge', fallback='200')
limit_sleep = config.get('Limits', 'Sleep', fallback='5')

target = None
try:
    with open('/proc/device-tree/hat/product', 'r') as infile:
        lines = str(infile.readlines())
        if "Pi Tail Production Tester Adapter" in lines:
            target = 'hat'
except:
    target = 'tag'

if not target:
    print("Hardware error: Unknown target")
    sys.exit(1)

def check_config(name, value):
    if value == '':
        print("Config error: Must set value for "+name)
        sys.exit(1)

check_config("FrequencyCounter", device_frequencycounter)
check_config("Multimeter", device_multimeter)
check_config("GPSDO", device_gpsdo)


firmware_to_flash = None
root = None
flash_process = None
flashing_event = None
test_update_event = None

if real_hardware:
    from gpiozero.pins.pigpio import PiGPIOFactory
    from gpiozero import LED, PWMLED, Device, InputDevice, OutputDevice
    Device.pin_factory = PiGPIOFactory()

def create_tf930():
    try:
        device = tf930.TF930.open_serial(device_frequencycounter, 115200, timeout=15)
    except Exception:
        device = None
    return device

def create_multimeter():
    try:
        device = instruments.generic_scpi.SCPIMultimeter.open_serial(device_multimeter, 115200)
    except Exception:
        device = None
    return device

def create_gpsdo():
    try:
        device = os.open(device_gpsdo, os.O_RDONLY | os.O_NONBLOCK)
    except Exception:
        device = None
    return device

frequencycounter = None
frequencycounter_lock = threading.Lock()

multimeter = None
multimeter_lock = threading.Lock()

gpsdo = None
gpsdo_lock = threading.Lock()

class MenuScreen(Screen):
    pass

class TestScreen(Screen):
    def __init__(self, **args):
        self.hardware_check_thread = None
        super(Screen,self).__init__(**args)

    def on_pre_enter(self):
        self.ids['status'].text = "[color=ffff00]Checking hardware[/color]"
        self.ids['output'].text = ""
        self.ready = False

    def on_enter(self):
        global hardware_check_event
        self.hardware_check_event = Clock.schedule_interval(root.ids['test_screen'].update, 1)
        self.hardware_check_thread = CheckHardware()
        self.hardware_check_thread.start()

    def on_leave(self):
        self.hardware_check_thread.stop()
        if self.hardware_check_event:
            self.hardware_check_event.cancel()

    def update(self, *args):
        if self.hardware_check_thread.initialised():
            status = self.hardware_check_thread.status()
            if status != '':
                self.ready = False
                self.ids['status'].text = "[color=ff0000]" + status + "[/color]"
            else:
                self.ready = True
                self.ids['status'].text = "Ready for testing a " + target

    def stop(self):
        if self.hardware_check_thread:
            self.hardware_check_thread.stop()

    pass

class FlashButton(Button):
    def on_release(self, *args):
        super(FlashButton, self).on_release(*args)
        global firmware_to_flash
        global flash_process
        global flashing_event
        firmware_to_flash = self.text
        if flash_process == None:
            flash_process = subprocess.Popen([flash_command, join(firmware_directory, firmware_to_flash)])
        root.ids['flash_screen'].ids['status'].text = 'Flashing  '
        root.ids['flash_screen'].ids['firmware'].text = firmware_to_flash
        flashing_event = Clock.schedule_interval(root.ids['flash_screen'].update, 0.2)

class FlashScreen(Screen):
    phase = 0

    def on_pre_enter(self):
        self.ids['files'].clear_widgets()
        files = os.listdir(firmware_directory)
        files.sort()
        for file in files:
            self.ids['files'].add_widget(FlashButton(text=file, font_size=30))
        self.ids['status'].text = ""
        self.ids['firmware'].text = "Choose your firmware"

    def update(self, *args):
        global flash_process
        rc = flash_process.poll()
        if rc == None:
            self.ids['status'].text = 'Flashing ' + ['/', '-', '\\', '|'][self.phase % 4]
            self.phase += 1
        else:
            if rc == 0:
                self.ids['status'].text = "[color=00ff00]Flashing complete[/color]"
            else:
                self.ids['status'].text = "[color=ff0000]FAIL[/color]"
            flash_process = None
            self.phase = 0
            flashing_event.cancel()

    pass

class DebugScreen(Screen):
    def add_buttons(self):
        self.buttons = []
        for name in relays.names():
            button = ToggleButton(text=name, font_size=30)
            button.bind(state=self.button_update)
            self.ids['debug_buttons'].add_widget(button)
            self.buttons.append(button)

    def button_update(self, instance, value):
        relays.relay(instance.text).state = True if value=='down' else False

    def set_pwm(self, value):
        pwmoutput.value = value

    def on_pre_enter(self):
        for button in self.buttons:
            state = relays.relay(button.text).state
            button.state = 'down' if state else 'normal'
        self.ids['pwm_slider'].value = pwmoutput.value

    pass

class TesterApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._finish_init)
        self.test = None

    def _finish_init(self, dt):
        self.root.ids['debug_screen'].add_buttons()
        global root
        root = self.root

    def start_test(self):
        global test_update_event
        if (self.test == None) or (not self.test.isAlive()):
            self.test = Test(self.root.ids['test_screen'].ids['output'].text)
            self.test.start()
            test_update_event = Clock.schedule_interval(self.update, 0.2)

    def update(self, *args):
        self.root.ids['test_screen'].ids['output'].text = self.test.output
        if not self.test.isAlive():
            test_update_event.cancel()

    def stop_test(self):
        if self.test != None:
            if self.test.isAlive():
                self.test.stop()

    def on_stop(self):
        self.stop_test()
        self.root.ids['test_screen'].stop()

    def shutdown(self):
        os.system("sudo shutdown now -h")

    pass

class RootWidget(Screen):
    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        Clock.schedule_once(self._finish_init)

    def _finish_init(self, dt):
        self.ids[debug_screen].add_buttons()

class PWMOutput:
    def __init__(self, name, gpio):
        self.pwm_name = name
        self.gpio = gpio
        self.pwm_value = 0
        if real_hardware:
            self.pin = PWMLED(gpio, initial_value=self.pwm_value, frequency=10000)

    def name(self):
        return self.pwm_name

    @property
    def value(self):
        return self.pwm_value

    @value.setter
    def value(self, value):
        self.pwm_value = value
        if real_hardware:
            self.pin.value = value

class GPIORelay(OutputDevice):
    def __init__(self, pin=None, initial_value=False, **args):
        super(OutputDevice, self).__init__(pin=pin, **args)
        self._write(initial_value)

    def _write(self, value):
        try:
            if value:
                self.pin.function = 'output'
                self.pin.state = False
            else:
                self.pin.function = 'input'
                self.pin.pull = 'floating'
        except AttributeError:
            self._check_open()
            raise

class InputPin:
    def __init__(self, name, gpio):
        self.pin_name = name
        self.gpio = gpio
        if real_hardware:
            self.pin = InputDevice(gpio, pull_up=None, active_state=True)

    def name(self):
        return self.pin_name

    @property
    def state(self):
        if real_hardware:
            return self.pin.value
        else:
            return False

class Relay:
    def __init__(self, name, gpio):
        self.relay_name = name
        self.gpio = gpio
        self.relay_state = False
        if real_hardware:
            self.pin = GPIORelay(gpio)

    def name(self):
        return self.relay_name

    @property
    def state(self):
        return self.relay_state

    @state.setter
    def state(self, value):
        self.relay_state = value
        if real_hardware:
            self.pin.value = value

    def on(self):
        self.state = True

    def off(self):
        self.state = False

    def toggle(self):
        self.state = not self.state

class Relays:
    def __init__(self, list=None):
        self.relays = []
        self.dict = dict()
        for (name, gpio) in list:
            self.add(Relay(name, gpio))

    def add(self, relay):
        name = relay.name()
        if name in self.dict.keys():
            raise Exception('Duplicate relay {}'.format(name))
        self.relays.append(relay)
        self.dict[name] = relay

    def names(self):
        return map(lambda x: x.name(), self.relays)

    def relay(self, name):
        return self.dict[name]

class Inputs:
    def __init__(self, list=None):
        self.inputs = []
        self.dict = dict()
        for (name, gpio) in list:
            self.add(InputPin(name, gpio))

    def add(self, obj):
        name = obj.name()
        if name in self.dict.keys():
            raise Exception('Duplicate input {}'.format(name))
        self.inputs.append(obj)
        self.dict[name] = obj

    def names(self):
        return map(lambda x: x.name(), self.input)

    def input(self, name):
        return self.dict[name]

class CheckHardware(threading.Thread):
    def __init__(self):
        self.output = ''
        self.stop_flag = False
        self.initialised_flag = False
        threading.Thread.__init__(self)

    def stop(self):
        self.stop_flag = True

    def initialised(self):
        return self.initialised_flag

    def status(self):
        return self.output

    def run(self):
        count = 0
        while self.stop_flag == False:
            if count == 0:
                self.update()
            time.sleep(1)
            count += 1
            if count > 5:
                count = 0

    def update(self):
        global frequencycounter
        global frequencycounter_lock
        global multimeter
        global multimeter_lock
        global gpsdo
        global gpsdo_lock
        output = []

        frequencycounter_lock.acquire()
        if frequencycounter == None:
            frequencycounter = create_tf930()
        frequencycounter_ok = False
        frequencycounter_reference = False
        if frequencycounter:
            try:
                name = frequencycounter.name
            except:
                name = None
                frequencycounter = None
            if name:
                try:
                    status = frequencycounter.status()
                    frequencycounter_ok = True
                except:
                    status = None
                    frequencycounter = None
                if status != None:
                    frequencycounter_reference = status['reference']
        frequencycounter_lock.release()

        multimeter_lock.acquire()
        if multimeter == None:
            multimeter = create_multimeter()
        multimeter_ok = False
        if multimeter:
            try:
                name = multimeter.name
            except Exception:
                try:
                    multimeter.sendcmd('*CLS')
                except Exception:
                    pass
                name = None
                multimeter = None
            if name:
                multimeter_ok = True
        multimeter_lock.release()

        gpsdo_lock.acquire()
        if gpsdo == None:
            gpsdo = create_gpsdo()
        gpsdo_ok = False
        if gpsdo:
            while True:
                try:
                    packet = os.read(gpsdo, 256)
                    gpsdo_ok = True
                    if len(packet) > 1:
                        gpsdo_gps_locked = not (packet[1] & 1)
                        gpsdo_pll_locked = not (packet[1] & 2)
                except OSError as err:
                    if err.errno == 11:
                        break
                    else:
                        os.close(gpsdo)
                        gpsdo = None
                        break
        gpsdo_lock.release()

        if not frequencycounter_ok: output.append('No Frequency Counter')
        if frequencycounter_ok and not frequencycounter_reference:
            output.append('No 10MHz Reference')

        if not multimeter_ok: output.append('No Multimeter')

        if not gpsdo_ok: output.append('No GPSDO')
        if gpsdo_ok and not gpsdo_gps_locked: output.append('No GPS lock')
        if gpsdo_ok and not gpsdo_pll_locked: output.append('No PLL lock')

        self.output = '\n'.join(output)
        self.initialised_flag = True

class Tag:
    def __init__(self, device):
        self.uart = serial.Serial(device, 9600, timeout=3)

    def close(self):
        self.uart.close()

    def sendctrlc(self):
        self.uart.write(('\003').encode('utf-8'))

    def firmware_send(self, cmd):
        time.sleep(0.2) # Allow time for the UART to finish transmitting
        self.uart.reset_input_buffer()
        self.uart.write((cmd + "\r\n").encode('utf-8'))

    def receive_match(self, target):
        found = False
        while True:
            rawline = self.uart.readline().decode('utf-8')
            line = rawline.rstrip()
            #self.output += "$${}$$".format(line)
            if target in line:
                found = True
                break
            if not ('\n' in rawline):
                break
        return found

    def firmware_cmd(self, cmd):
        time.sleep(0.2) # Allow time for the UART to finish transmitting
        self.uart.reset_input_buffer()
        self.uart.write((cmd + "\r\n").encode('utf-8'))
        #self.output += cmd + "\r\n"
        result = []
        while True:
            rawline = self.uart.readline().decode('utf-8')
            line = rawline.rstrip()
            #self.output += rawline
            if line == ">":
                break
            if not ('\n' in rawline):
                break
            result.append(line)
        #self.output += ">>>{}<<<".format(str(result))
        if not result:
            return None
        if result.pop(0) != cmd:
            return None
        if result == ['Unrecognised command']:
            return None
        return result

    def rgpio(self, led, mode, direction, value):
        if self.firmware_cmd('rgpio {} {} {} {}'.format(led, mode, direction, value)) == None:
            return False
        return True

    def set_xtal(self, xtal):
        if self.firmware_cmd('xtal {}'.format(xtal)) == None:
            return False
        return True

    def prepare_xtal_trim(self):
        self.firmware_cmd('stop')
        self.firmware_cmd('wake')

    def read_config(self, key):
        return self.firmware_cmd('config {}'.format(key))

    def write_config(self, key, value):
        value = ' '.join(str(x) for x in value)
        if self.firmware_cmd('config {} {}'.format(key, value)) != []:
            return False
        return True

    def flush_config(self):
        return True

    def read_eui(self):
        eui = self.read_config('eui')
        if eui == None:
            return None
        if eui[0] != "Key not found":
            if (eui[0].startswith('eui: ')):
                oe = eui[0][5:]
                return netaddr.EUI('-'.join(reversed(oe.split())))
        return None

    def write_eui(self, eui):
        value = reversed(list(eui.words))
        return self.write_config('eui', value)

    def write_xtal_ppm(self, ppm):
        return self.write_config('xtal_ppm', [ppm % 256, int(ppm / 256)])

    def reading(self, name):
        r_value = self.firmware_cmd(name)
        if not r_value:
            return None # Read failure
        try:
            value = float(r_value[0])
        except:
            return None # Parse error
        return value

    def rawbattery(self):
        return self.reading('rawbattery')

    def volts(self):
        return self.reading('volts')

    def rawvolts(self):
        return self.reading('rawvolts')

    def temp(self):
        return self.reading('temp')

    def rawtemp(self):
        return self.reading('rawtemp')

GPIO_CTRL = 0x26
GPIO_MODE = 0x00
GPIO_DIR  = 0x08
GPIO_DOUT = 0x0C

FS_CTRL   = 0x2B
FS_XTALT  = 0x0E

configmap = {
    'eui'        : 'decawave,eui64',
    'xtal_trim'  : 'decawave,xtalt',
    'xtal_ppm'   : 'decawave,xtal_ppm',
    'xtal_volts' : 'decawave,xtal_volts',
    'xtal_temp'  : 'decawave,xtal_temp',
}

class Hat:
    def __init__(self, bus, device):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 1000000
        self.spi.mode = 0
        self.config = {}
        self.eeprom = None

    def close(self):
        self.spi.close()
        if self.eeprom:
            self.eeprom.overlay.remove()

    def header(self, file, reg, write):
        b = [file]
        if write:
            b[0] = b[0] | 0x80
        if reg is not 0:
            b[0] = b[0] | 0x40
            b.append(reg & 0x7f)
            if reg >> 7 is not 0:
                b.append(reg >> 7)
                b[1] = b[1] | 0x80
        return b

    def read(self, file, reg, bytes):
        h = self.header(file, reg, False)
        hlen = len(h)
        data = h + [0] * bytes
        result = self.spi.xfer2(data)
        del result[:hlen]
        return result

    def write(self, file, reg, bytes):
        h = self.header(file, reg, True)
        data = h + bytes
        result = self.spi.xfer2(data)

    def identify(self):
        result = self.read(0, 0, 4)
        return result == [48, 1, 202, 222]

    def rgpio(self, pin, mode, direction, value):
        if (pin < 0) or (pin > 8):
            return False
        modepin = (pin + 3) * 2
        reg = self.read(GPIO_CTRL, GPIO_MODE, 4)
        reg = int.from_bytes(reg, byteorder='little')
        reg = reg & ~(3 << modepin)
        reg = reg | (mode << modepin)
        self.write(GPIO_CTRL, GPIO_MODE, list(reg.to_bytes(4, byteorder='little')))

        dirpin = pin
        if pin > 3:
            dirpin += 4
        if pin > 7:
            dirpin += 4
        dir = (direction << dirpin) | (1 << (dirpin + 4))
        dout = (value << dirpin) | (1 << (dirpin + 4))
        self.write(GPIO_CTRL, GPIO_DIR, list(dir.to_bytes(4, byteorder='little')))
        self.write(GPIO_CTRL, GPIO_DOUT, list(dout.to_bytes(4, byteorder='little')))
        return True

    def set_xtal(self, xtal):
        self.write(FS_CTRL, FS_XTALT, [xtal | 0x60])

    def prepare_xtal_trim(self):
        relays.relay('uart').state = True
        pass

    def create_eeprom(self):
        return EepromDevice(bus=98, autoload=False, autosave=False)

    def load_eeprom(self):
        if self.eeprom != None:
            return
        try:
            self.eeprom = self.create_eeprom().load()
        except EepromValueError:
            self.eeprom = self.create_eeprom()
            with open(eeprom_yaml, 'r') as f:
                desc = EepromDescription(yaml=f.read())
            desc.apply(self.eeprom)
            with open(eeprom_dts, 'r') as f:
                process = subprocess.run(['dtc', '-@'], stdin=f, check=True, capture_output=True)
                self.eeprom.fdt = parse_dtb(process.stdout)
        self.eeprom_path = self.eeprom.fdt.get_property('dw1000', '__symbols__').value

    def read_eeprom(self, key):
        self.load_eeprom()
        prop = self.eeprom.fdt.get_property(key, path=self.eeprom_path)
        if prop:
            return list(prop)
        else:
            return None

    def write_eeprom(self, key, value):
        self.load_eeprom()
        self.eeprom.fdt.set_property(key, value, path=self.eeprom_path)

    def write_config(self, key, value):
        key = configmap[key]
        self.config[key] = value
        return True

    def flush_config(self):
        for key, value in self.config.items():
            self.write_eeprom(key, value)
        try:
            self.eeprom.save(verify=True)
        except EepromVerificationError:
            return False
        return True

    def read_eui(self):
        eui = self.read_eeprom('decawave,eui64')
        if eui:
            try:
                eui = '-'.join(format(s, '02x') for s in b''.join(part.to_bytes(4, 'big') for part in eui))
                return netaddr.EUI(eui, version=64)
            except:
                return None
        return None

    def write_eui(self, eui):
        return self.write_config('eui', list(struct.unpack('>2I', struct.pack('>Q', int(eui)))))

    def write_xtal_ppm(self, ppm):
        return self.write_config('xtal_ppm', [ppm])

    def read_adc(self):
        self.write(0x28, 0x11, [0x80])
        self.write(0x28, 0x11, [0x0a])
        self.write(0x28, 0x11, [0x0f])
        self.write(0x2a, 0x00, [0x01])
        self.write(0x2a, 0x00, [0x00])
        voltage     = self.read(0x2a, 0x03, 1)[0]
        temperature = self.read(0x2a, 0x04, 1)[0]
        return (voltage, temperature)

    def read_otp(self, address, bytes):
        self.write(0x2d, 0x04, [address & 0xff, address >> 8])
        self.write(0x2d, 0x06, [3])
        return self.read(0x2d, 0x0a, bytes)

    def read_adc(self):
        self.write(0x28, 0x11, [0x80])
        self.write(0x28, 0x12, [0x0a])
        self.write(0x28, 0x12, [0x0f])
        self.write(0x2a, 0x00, [0x01])
        self.write(0x2a, 0x00, [0x00])
        voltage     = self.read(0x2a, 0x03, 1)[0]
        temperature = self.read(0x2a, 0x04, 1)[0]
        return (voltage, temperature)

    def volts_cal(self):
        return self.read_otp(0x08, 1)[0]

    def temp_cal(self):
        return self.read_otp(0x09, 1)[0]

    def volts(self):
        return (self.rawvolts() - self.volts_cal()) / 173 + 3.3

    def rawvolts(self):
        return self.read_adc()[0]

    def temp(self):
        return 1000 * (self.rawtemp() - self.temp_cal()) / 1140 + 23

    def rawtemp(self):
        return self.read_adc()[1]

    def sleep(self):
        self.write(0x2c, 0x00, [0, 0])
        self.write(0x2c, 0x06, [3]) # Wakeup on pin, sleep enable
        self.write(0x2c, 0x02, [0])
        self.write(0x2c, 0x02, [2]) # Save

    def assert_irq(self, state):
        self.rgpio(8, 1, 0, state)

class Test(threading.Thread):
    def __init__(self, output):
        self.output = output
        self.stopping = False
        threading.Thread.__init__(self)

    def stop(self):
        self.stopping = True

    def voltage(self, range=5):
        time.sleep(0.2)
        volts = float(multimeter.query('MEAS:VOLT:DC? {}'.format(range)))
        #self.output += " {}V".format(volts)
        return volts

    def diode(self):
        time.sleep(0.2)
        volts = float(multimeter.query('MEAS:DIODE?'))
        #self.output += " {}V".format(volts)
        multimeter.sendcmd('CONF:VOLT:DC 5')
        return volts

    def frequency_setup(self):
        frequencycounter.set(frequencycounter.Coupling.ac)
        frequencycounter.set(frequencycounter.Attenuation.atten_5to1)
        frequencycounter.set(frequencycounter.Impedance.imp_1m)
        frequencycounter.set(frequencycounter.Edge.rising)
        frequencycounter.set(frequencycounter.LowPass.lpf_out)
        frequencycounter.threshold_offset = 0
        frequencycounter.mode = frequencycounter.Mode.a_frequency

    def frequency(self):
        time.sleep(0.3)
        frequencycounter.set(frequencycounter.MeasurementTime.t_10s)
        frequencycounter.set(frequencycounter.MeasurementTime.t_300ms)
        freq = float(frequencycounter.measure())
        #self.output += " {}Hz".format(freq)
        return freq

    def all_relays_off(self):
        for name in relays.names():
            relays.relay(name).state = False
        return True

    def check_no_battery(self):
        result = False
        relays.relay('power_3v7').state = False
        relays.relay('neg_ground').state = True
        relays.relay('measure_bat').state = True
        v_max = 0
        v_min = float('Inf')
        t_max = 1.0
        t_diff = 0.5
        for _ in range(30):
            v_off = self.voltage()
            if v_off < v_min:
                v_min = v_off
            if v_off > v_max:
                v_max = v_off
            if v_off < t_max:
                break
            if v_max - v_min > t_diff:
                break
            time.sleep(1)
        relays.relay('measure_bat').state = False
        relays.relay('neg_ground').state = False
        if v_off < t_max:
            return True
        if v_max - v_min > t_diff:
            return True
        return False

    def check_off(self):
        result = False
        relays.relay('short_3v3').state = True
        time.sleep(0.5)
        relays.relay('short_3v3').state = False
        time.sleep(0.2)
        relays.relay('power_3v7').state = True
        relays.relay('neg_ground').state = True
        relays.relay('measure_bat').state = True
        v_on = self.voltage()
        relays.relay('measure_bat').state = False
        if v_on > 3.5:
            relays.relay('measure_batsw').state = True
            v_off = self.voltage()
            relays.relay('measure_batsw').state = False
            if v_off < 1.0:
                result = True
        relays.relay('neg_ground').state = False
        relays.relay('power_3v7').state = False
        return result

    def set_voltage(self, target):
        neg_isense = relays.relay('neg_isense-').state
        neg_ground = relays.relay('neg_ground').state
        relays.relay('neg_isense-').state = False
        relays.relay('neg_ground').state = True
        pwmoutput.value = 0.5
        for _ in range(2):
            v = self.voltage()
            #self.output += " {} * ({} / {}) = {} * {} = {}\n".format(pwmoutput.value, target, v, pwmoutput.value, (target / v), pwmoutput.value * (target / v))
            #self.output += " {} {}\n".format(v, pwmoutput.value)
            n = 1
            pwmoutput.value = (pwmoutput.value * (target / v)) * n + (pwmoutput.value) * (1-n)
        relays.relay('neg_ground').state = neg_ground
        relays.relay('neg_isense-').state = neg_isense

    def test_charger(self):
        relays.relay('pullup_5v').state = True
        relays.relay('measure_isense+').state = True
        relays.relay('neg_ground').state = True
        self.set_voltage(2.2)
        v_set = self.voltage()
        if (v_set < 1.9) or (v_set > 2.5):
            return False
        relays.relay('dummy_load').state = True
        relays.relay('power_5v').state = True
        relays.relay('pullup_5v').state = False
        v_set_on = self.voltage()
        if (v_set_on < 2.2) or (v_set_on > 2.8):
            return False
        relays.relay('neg_ground').state = False
        relays.relay('neg_isense-').state = True
        i_precond = 1000 * self.voltage(0.5) / 0.2
        self.set_voltage(3.7)
        i_charge = 1000 * self.voltage(0.5) / 0.2
        self.output += "{:f} / {:f} mA".format(i_precond, i_charge)
        relays.relay('power_5v').state = False
        relays.relay('dummy_load').state = False
        relays.relay('neg_isense-').state = False
        relays.relay('measure_isense+').state = False
        self.record({
            'charger' : {
                'preconditioning' : i_precond,
                'charging'        : i_charge
            }})
        if i_precond > float(limit_precondition):
            return False
        if i_charge > float(limit_charge):
            return False
        return True

    # Leaves the power on for the next test
    def test_regulator(self, power_relay):
        relays.relay(power_relay).state = True
        relays.relay('dut_on').state = True
        relays.relay('neg_ground').state = True
        relays.relay('measure_3v3').state = True
        v = self.voltage()
        relays.relay('measure_3v3').state = False
        relays.relay('neg_ground').state = False
        self.record({ '3v3' : v })
        if (v < 3.2) or (v > 3.4):
            return False
        return True

    def tag_test_regulator(self):
        return self.test_regulator('power_3v7')

    def hat_test_regulator(self):
        return self.test_regulator('power_5v')

    def test_hat_alive(self):
        relays.relay('jtag').state = True
        relays.relay('reset').state = True
        time.sleep(0.1)
        relays.relay('reset').state = False
        time.sleep(0.1)
        return self.dut.identify()

    def test_hat_power(self):
        relays.relay('power_5v').state = False
        time.sleep(0.1)
        if self.dut.identify():
            return False
        relays.relay('power_5v').state = True
        relays.relay('reset').state = True
        time.sleep(0.1)
        relays.relay('reset').state = False
        time.sleep(0.1)
        return self.dut.identify()

    def test_hat_reset(self):
        relays.relay('reset').state = True
        time.sleep(0.1)
        if self.dut.identify():
            return False
        relays.relay('reset').state = False
        time.sleep(0.1)
        return self.dut.identify()

    def test_hat_irq(self):
        if inputs.input('irq').state:
            return False
        self.dut.assert_irq(True)
        if not inputs.input('irq').state:
            return False
        self.dut.assert_irq(False)
        if inputs.input('irq').state:
            return False
        return True

    # If we ever have a hat with the wakeup line connected...
    def test_hat_wakeup(self):
        self.dut.sleep()
        time.sleep(0.1)
        if self.dut.identify():
            return False
        # Turn on wakeup line
        time.sleep(0.1)
        return self.dut.identify()
        
    def flash(self):
        relays.relay('dut_on').state = True
        relays.relay('jtag').state = True
        time.sleep(0.2)
        proc = subprocess.run([flash_command, join(firmware_directory, production_firmware)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        relays.relay('jtag').state = False
        relays.relay('dut_on').state = False
        if proc.returncode == 0:
            return True
        self.output += "\n"
        if proc.stdout != None:
            self.output += proc.stdout.decode('utf-8')
        return False

    def drain(self):
        relays.relay('power_5v').state = False
        relays.relay('pullup_5v').state = False
        relays.relay('power_3v7').state = False
        relays.relay('dut_on').state = False
        relays.relay('dut_sense').state = False
        relays.relay('short_3v3').state = True
        time.sleep(0.2)
        relays.relay('short_3v3').state = False
        return True

    # Leaves the power and UART on for the next tests
    def test_firmware_boot(self):
        relays.relay('power_3v7').state = True
        relays.relay('dut_on').state = True
        relays.relay('uart').state = True
        time.sleep(4)
        if self.dut.firmware_cmd('stop') == None:
            return False
        # The firmware needs to bring the radio out of sleep a couple of
        # times before the voltage and temperature readings are valid
        self.dut.firmware_cmd('prepare')
        self.dut.firmware_cmd('prepare')
        return True

    def test_battery_adc(self):
        relays.relay('neg_ground').state = True
        relays.relay('measure_bat').state = True
        v_reg = self.voltage()
        v_adc = self.dut.rawbattery()
        if not v_adc:
            self.output += " Failed to get ADC reading"
            return False
        relays.relay('measure_bat').state = False
        relays.relay('neg_ground').state = False
        v_adc = v_adc / 1000
        self.output += " {} ({}) {:.2%}".format(v_adc, v_reg, (v_adc - v_reg) / v_reg)
        self.record({
            'battery_adc' : {
                'v_reg' : v_reg,
                'v_adc' : v_adc
            }})
        return abs(v_reg - v_adc) < 0.1

    def test_radio_adc(self):
        relays.relay('neg_ground').state = True
        relays.relay('measure_3v3').state = True
        v_reg = self.voltage()
        v_volts = self.dut.volts()
        if not v_volts:
            self.output += " Failed to get voltage reading"
            return False
        v_rawvolts = self.dut.rawvolts()
        if not v_rawvolts:
            self.output += " Failed to get raw voltage reading"
            return False
        t_temp = self.dut.temp()
        if not t_temp:
            self.output += " Failed to get temperature reading"
            return False
        t_rawtemp = self.dut.rawtemp()
        if not t_rawtemp:
            self.output += " Failed to get raw temperature reading"
            return False
        self.output += " {}V / {}°C".format(v_volts, t_temp)
        self.output += " {} / {}".format(v_rawvolts, t_rawtemp)
        relays.relay('measure_3v3').state = False
        relays.relay('neg_ground').state = False
        self.record({
            'radio_adc' : {
                'v_reg' : v_reg,
                'v_volts' : v_volts,
                't_temp' : t_temp,
                'v_rawvolts' : v_rawvolts,
                't_rawtemp' : t_rawtemp,
            }})
        if not self.dut.write_config('xtal_volts', [v_rawvolts]):
            return False
        if not self.dut.write_config('xtal_temp', [t_rawtemp]) != []:
            return False
        return abs(v_reg - v_volts) < 0.1

    def xtal_trim(self):
        output = self.output
        self.dut.prepare_xtal_trim()
        self.dut.rgpio(0, 2, 0, 0)
        self.frequency_setup()
        f_target = 62.4 * 1000 * 1000
        xtal = 15
        xtal_min = 0
        xtal_max = 31
        f = None
        f_last = None
        xtal_last = None
        while True:
            self.dut.set_xtal(xtal)
            f_last = f
            f = self.frequency()
            ppm = 1000000 * ((f - f_target) / f_target)
            #self.output = output + "\n{}: {} ({:.02f} ppm)".format(xtal, f, ppm)
            self.output = output + " {}: {:.02f} ppm".format(xtal, ppm)
            if abs(f - f_target) > 10000:
                return False
            if f > f_target:
                if f_last and (f_last < f_target):
                    break
                new_xtal = xtal + 1
            else:
                if f_last and (f_last > f_target):
                    break
                new_xtal = xtal - 1
            if (new_xtal > xtal_max) or (new_xtal < xtal_min):
                return False
            xtal_last = xtal
            xtal = new_xtal
        if abs(f - f_target) > abs(f_last - f_target):
            xtal = xtal_last
            f = f_last
        self.dut.set_xtal(xtal)
        self.record({
            'xtal' : {
                'trim' : xtal,
                'frequency' : f
            }})
        self.xtal = xtal
        ppm = 1000000 * ((f - f_target) / f_target)
        xtal_ppm = round(ppm * 100) % 65536
        self.output = output + " {}: {:.02f} ppm".format(xtal, ppm)
        self.dut.rgpio(0, 1, 0, 0)
        if not self.dut.write_config('xtal_trim', [xtal]):
            return False
        if not self.dut.write_xtal_ppm(xtal_ppm):
            return False
        return True

    def xtal_sweep(self):
        output = self.output
        self.dut.prepare_xtal_trim()
        self.dut.rgpio(0, 2, 0, 0)
        self.frequency_setup()
        f_target = 62.4 * 1000 * 1000
        sweep = []
        for xtal in range(32):
            self.dut.set_xtal(xtal)
            f = self.frequency()
            ppm = 1000000 * ((f - f_target) / f_target)
            self.output = output + " {}: {:.02f} ppm".format(xtal, ppm)
            sweep.append(f)

        self.dut.set_xtal(xtal)
        self.record({
            'xtal_sweep' : sweep
            })
        self.dut.rgpio(0, 1, 0, 0)
        return True

    def read_chip_id(self):
        id = self.dut.firmware_cmd('chipid')
        if not id:
            return False
        id = id[0]
        if not id:
            return False
        self.record({ 'chipid' : id })
        self.output += " {}".format(id)
        return True

    def assign_eui(self):
        oldeui = self.dut.read_eui()
        if oldeui:
            self.output += " (preserved)"
            self.eui = oldeui
        else:
            self.eui = self.get_next_eui()
        if not self.eui:
            return False
        self.record( { 'eui' : str(self.eui) })
        self.output += " {}".format(self.eui)
        if not self.dut.write_eui(self.eui):
            return False
        return True

    def program_config(self):
        try:
            with open(config_file, 'r') as infile:
                lines = infile.readlines()
        except:
            self.output += "\n[color=#ff0000]Unable to read config file {}[/color]".format(config_file)
            return False
        for line in lines:
            result = self.dut.firmware_cmd(line.strip())
            if result != []:
                return False
        return self.dut.flush_config()

    def program_eeprom(self):
        return self.dut.flush_config()

    def test_leds(self):
        relays.relay('neg_ground').state = True
        leds = [0, 1, 2, 3]
        # Set all LEDs high impedance
        for led in leds:
            if not self.dut.rgpio(led, 0, 1, 0):
                return False
        for led in leds:
            self.output += " {}".format(led)
            relays.relay('measure_led{}'.format(led)).state = True
            if not self.dut.rgpio(led, 0, 0, 0):
                return False
            v = self.voltage()
            if v > 0.5:
                self.output += " LED {} not low".format(led)
                return False
            if not self.dut.rgpio(led, 0, 0, 1):
                return False
            v = self.voltage()
            if v < 2.5:
                self.output += " LED {} not high".format(led)
                return False
            if not self.dut.rgpio(led, 0, 1, 0):
                return False
            for l in leds:
                if l != led:
                    #self.output += " ({} on)".format(l)
                    if not self.dut.rgpio(l, 0, 0, 1):
                        return False
            v = self.voltage()
            if v > 0.5:
                self.output += "LED {} shorted".format(led)
                return False
            for l in leds:
                if not self.dut.rgpio(l, 0, 1, 0):
                    return False
            v = self.diode()
            if v < 1.0:
                self.output += "LED {} not connected".format(led)
                return False
            relays.relay('measure_led{}'.format(led)).state = False
        for led in leds:
            if not self.dut.rgpio(led, 1, 0, 0):
                return False
        relays.relay('neg_ground').state = False
        return True

    def test_sleep_current(self):
        v = self.voltage(0.5)
        self.dut.firmware_cmd('stop')
        self.dut.firmware_cmd('sleep')
        relays.relay('neg_batsw').state = True
        relays.relay('measure_bat').state = True
        relays.relay('dut_sense').state = True
        uart = relays.relay('uart').state
        relays.relay('uart').state = False
        time.sleep(0.5)
        relays.relay('dut_on').state = False
        time.sleep(0.2)
        i_sleep = 1000 * self.voltage(0.5) / 10
        relays.relay('dut_on').state = True
        time.sleep(0.2)
        relays.relay('dut_sense').state = False
        relays.relay('measure_bat').state = False
        relays.relay('neg_batsw').state = False
        relays.relay('uart').state = uart
        self.record({ 'sleep_current' : i_sleep })
        self.output += " {:.3f} uA".format(i_sleep)
        return i_sleep <= float(limit_sleep)

    def test_bootloader_entry(self):
        self.dut.firmware_send('reset')
        for _ in range(10):
            self.dut.sendctrlc()
            time.sleep(0.5)
        if self.dut.receive_match('ChipID'):
            return True
        return False

    def test_firmware_entry(self):
        self.dut.firmware_send('reset')
        time.sleep(3)
        if self.dut.receive_match('Ready for action'):
            return True
        return False

    tests_tag = [
                all_relays_off,
                check_no_battery,
                check_off,
                test_charger,
                tag_test_regulator,
                flash,
                drain,
                test_firmware_boot,
                test_battery_adc,
                test_radio_adc,
                xtal_trim,
                xtal_sweep,
                read_chip_id,
                test_leds,
                test_sleep_current,
                assign_eui,
                program_config,
                test_firmware_entry,
                test_bootloader_entry,
                drain,
            ]

    tests_hat = [
                all_relays_off,
                hat_test_regulator,
                test_hat_alive,
                test_hat_power,
                test_hat_reset,
                test_hat_irq,
                #test_hat_wakeup,
                test_radio_adc,
                xtal_trim,
                xtal_sweep,
                test_leds,
                assign_eui,
                program_eeprom,
            ]

    def cleanup(self):
        # Reset all hardware to a safe state
        pass

    def run(self):
        try:
            self.read_log()
        except:
            self.output += "\n[color=#ff0000]Please ensure results file {} exists and contains valid JSON[/color]".format(results_file)
            return
        self.results = dict()
        frequencycounter_lock.acquire()
        multimeter_lock.acquire()
        gpsdo_lock.acquire()
        all_pass = True
        self.eui = None
        try:
            if target == 'hat':
                self.tests = self.tests_hat
                self.dut = Hat(0, 0)
            else:
                self.tests = self.tests_tag
                self.dut = Tag(device_dut)
        except:
            self.output += "\n[color=#ff0000]Failed to initialise DUT[/color]"
            self.stopping = True

        if (frequencycounter == None) or (multimeter == None) or (gpsdo == None):
            self.output += "\n[color=#ff0000]Test equipment not available.[/color]"
            self.stopping = True
        for test in self.tests:
            if self.stopping:
                self.output += "\n[color=#ff0000]TEST ABORTED[/color]"
                break
            self.output += "\n{0:.<20s}".format(test.__name__)
            try:
                result = test(self)
            except Exception as e:
                self.output += " [color=#ff0000]Exception: {}[/color]".format(e)
                print(e)
                traceback.print_exc()
                result = False
            if result:
                self.output += " [color=#00ff00]OK[/color]"
            else:
                all_pass = False
                self.output += " [color=#ff0000]FAIL[/color]"
                break
        self.dut.close()
        self.all_relays_off()
        if all_pass:
            self.log.update({str(self.eui) : self.results})
            self.write_log()
            self.output += "\n[color=#00ff00]TEST PASSED[/color] [color=#ffff00]{}[/color]".format(self.eui)
        else:
            self.output += "\n[color=#ff0000]TEST FAILED[/color]"
        gpsdo_lock.release()
        multimeter_lock.release()
        frequencycounter_lock.release()
        self.cleanup()

    def get_next_eui(self):
        # if self.chipid in database:
        #    return lookup(self.chipid).eui
        with open(eui_file, 'r') as infile:
            euitext = infile.read()
            try:
                eui = netaddr.EUI(euitext, version=64)
            except:
                return None
            nexteui = netaddr.EUI(int(eui)+1, version=64)
            nexteui_file = eui_file + '.tmp'
            with open(nexteui_file, 'w') as outfile:
                outfile.write(str(nexteui))
            os.rename(nexteui_file, eui_file)
        return eui

    def record(self, dict):
        self.results.update(dict)

    def read_log(self):
        with open(results_file, 'r') as infile:
            self.log = json.load(infile)

    def write_log(self):
        newresults_file = results_file + '.tmp'
        with open(newresults_file, 'w') as outfile:
            json.dump(self.log, outfile, indent=4, sort_keys=True)
        os.rename(newresults_file, results_file)

pwmoutput = PWMOutput('pwm', 18)

if target == 'hat':
    relays = Relays(
        [
            ('power_5v',         17),
            ('dut_on',           23),
            ('reset',            24),
            ('measure_3v3',       7),
            ('measure_led3',      5),
            ('measure_led2',      6),
            ('measure_led1',     12),
            ('measure_led0',     13),
            ('neg_ground',       26),
            ('jtag',             21),
            ('uart',             20),
        ])
    inputs = Inputs(
        [
            ('irq',              25),
        ])

else:
    relays = Relays(
        [
            ('power_5v',         17),
            ('pullup_5v',        27),
            ('power_3v7',        22),
            ('dummy_load',       23),
            ('dut_on',           24),
            ('dut_sense',        10),
            ('short_3v3',         9),
            ('measure_isense+',  25),
            ('measure_bat',      11),
            ('measure_batsw',     8),
            ('measure_3v3',       7),
            ('measure_led3',      5),
            ('measure_led2',      6),
            ('measure_led1',     12),
            ('measure_led0',     13),
            ('neg_isense-',      19),
            ('neg_batsw',        16),
            ('neg_ground',       26),
            ('jtag',             21),
            ('uart',             20),
        ])

if __name__ == '__main__':
    TesterApp().run()
