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
from subprocess import Popen
import sys

import threading
import time

import configparser

import tf930
import instruments

config = configparser.ConfigParser()
config.read('tester.ini')

real_hardware = config.getboolean('Tester', 'RealHardware', fallback=True)
firmware_directory = expanduser(config.get('Tester', 'FirwareDirectory', fallback='~/firmware'))
flash_command = config.get('Tester', 'FlashCommand', fallback='./flash.sh')

device_frequencycounter = config.get('Tester', 'FrequencyCounter', fallback='')
device_multimeter = config.get('Tester', 'Multimeter', fallback='')
device_gpsdo = config.get('Tester', 'GPSDO', fallback='')

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
    from gpiozero import LED

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
                self.ids['status'].text = "Ready for testing"

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
            flash_process = Popen([flash_command, join(firmware_directory, firmware_to_flash)])
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
        for name in relays.names():
            self.ids['debug_buttons'].add_widget(ToggleButton(text=name, font_size=30))
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

    pass

class RootWidget(Screen):
    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        Clock.schedule_once(self._finish_init)

    def _finish_init(self, dt):
        self.ids[debug_screen].add_buttons()

class Relay:
    def __init__(self, name, gpio):
        self.relay_name = name
        self.gpio = gpio
        self.state = False
        if real_hardware:
            self.pin = LED(gpio)

    def name(self):
        return self.relay_name

    def state(self):
        return self.state

    def on(self):
        self.state = True
        if real_hardware:
            self.pin.on()

    def off(self):
        self.state = False
        if real_hardware:
            self.pin.off()

    def toggle(self):
        self.state = not self.state
        if real_hardware:
            self.pin.toggle()

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

class Test(threading.Thread):
    def __init__(self, output):
        self.output = output
        threading.Thread.__init__(self)

    def run(self):
        self.output = "Yay"
        time.sleep(2)
        self.output += "\nWe're here!"
        time.sleep(2)
        self.output += "\nAlive"
        time.sleep(2)
        self.output += "\nAnd kicking"
        time.sleep(2)
        self.output += "\nIn a thread"
        time.sleep(2)
        self.output += "\n... and we're done"

relays = Relays(
    [
        ('power_5v',         1),
        ('pullup_5v',        23),
        ('power_3v7',        24),
        ('dummy_load',       4),
        ('dut_on',           5),
        ('dut_sense',        6),
        ('short_3v3',        7),
        ('measure_isense+',  8),
        ('measure_bat',      9),
        ('measure_batsw',   10),
        ('measure_3v3',     11),
        ('measure_led3',    12),
        ('measure_led2',    13),
        ('measure_led1',    14),
        ('measure_led0',    15),
        ('neg_isense-',     16),
        ('neg_batsw',       17),
        ('neg_ground',      18),
        ('jtag',            19),
        ('uart',            25),
    ])

if __name__ == '__main__':
    TesterApp().run()
