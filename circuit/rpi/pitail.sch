EESchema Schematic File Version 2
LIBS:power
LIBS:device
LIBS:transistors
LIBS:conn
LIBS:linear
LIBS:regul
LIBS:74xx
LIBS:cmos4000
LIBS:adc-dac
LIBS:memory
LIBS:xilinx
LIBS:microcontrollers
LIBS:dsp
LIBS:microchip
LIBS:analog_switches
LIBS:motorola
LIBS:texas
LIBS:intel
LIBS:audio
LIBS:interface
LIBS:digital-audio
LIBS:philips
LIBS:display
LIBS:cypress
LIBS:siliconi
LIBS:opto
LIBS:atmel
LIBS:contrib
LIBS:valves
LIBS:_wireless
LIBS:pitail-cache
EELAYER 25 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title "DWM1000 Pi Hat"
Date ""
Rev ""
Comp "Unipart Digital"
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L Raspberry_Pi_2_3 J0
U 1 1 59FF759C
P 6900 3350
F 0 "J0" H 7600 2100 50  0000 C CNN
F 1 "Raspberry_Pi_2_3" H 6500 4250 50  0000 C CNN
F 2 "Pin_Headers:Pin_Header_Straight_2x20_Pitch2.54mm" H 7900 4600 50  0001 C CNN
F 3 "" H 6950 3200 50  0001 C CNN
	1    6900 3350
	-1   0    0    -1  
$EndComp
$Comp
L DWM1000 U0
U 1 1 59FF75F5
P 2450 3650
F 0 "U0" H 3150 4200 60  0000 C CNN
F 1 "DWM1000" H 2450 4050 60  0000 C CNN
F 2 "_div:DWM1000" H 3500 3150 60  0001 C CNN
F 3 "" H 3500 3150 60  0001 C CNN
	1    2450 3650
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR01
U 1 1 59FF7F45
P 7300 4900
F 0 "#PWR01" H 7300 4900 30  0001 C CNN
F 1 "GND" H 7300 4830 30  0001 C CNN
F 2 "" H 7300 4900 60  0001 C CNN
F 3 "" H 7300 4900 60  0001 C CNN
	1    7300 4900
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR02
U 1 1 59FF80CC
P 1350 4900
F 0 "#PWR02" H 1350 4900 30  0001 C CNN
F 1 "GND" H 1350 4830 30  0001 C CNN
F 2 "" H 1350 4900 60  0001 C CNN
F 3 "" H 1350 4900 60  0001 C CNN
	1    1350 4900
	1    0    0    -1  
$EndComp
$Comp
L +3.3V #PWR03
U 1 1 59FF8571
P 1350 3800
F 0 "#PWR03" H 1350 3760 30  0001 C CNN
F 1 "+3.3V" H 1350 3910 30  0000 C CNN
F 2 "" H 1350 3800 60  0001 C CNN
F 3 "" H 1350 3800 60  0001 C CNN
	1    1350 3800
	1    0    0    -1  
$EndComp
Text Label 3500 3250 0    60   ~ 0
CSn
Text Label 3500 3350 0    60   ~ 0
MOSI
Text Label 3500 3450 0    60   ~ 0
MISO
Text Label 3500 3550 0    60   ~ 0
SCLK
Text Label 3500 3750 0    60   ~ 0
IRQ
$Comp
L LED_Small D0
U 1 1 59FF99FA
P 4600 5800
F 0 "D0" H 4550 5925 50  0000 L CNN
F 1 "LED_Small" H 4425 5700 50  0000 L CNN
F 2 "LEDs:LED_0805" V 4600 5800 50  0001 C CNN
F 3 "" V 4600 5800 50  0001 C CNN
	1    4600 5800
	-1   0    0    -1  
$EndComp
Wire Wire Line
	3450 3550 6000 3550
Wire Wire Line
	3450 3250 6000 3250
Wire Wire Line
	3450 3350 5500 3350
Wire Wire Line
	5500 3350 5500 3450
Wire Wire Line
	5500 3450 6000 3450
Wire Wire Line
	3450 3450 5400 3450
Wire Wire Line
	5400 3450 5400 3400
Wire Wire Line
	5400 3400 5600 3400
Wire Wire Line
	5600 3400 5600 3350
Wire Wire Line
	5600 3350 6000 3350
Wire Wire Line
	8150 3450 8150 5550
Wire Wire Line
	6600 4650 6600 4750
Wire Wire Line
	6600 4750 7300 4750
Wire Wire Line
	7300 4650 7300 4900
Wire Wire Line
	7200 4650 7200 4750
Connection ~ 7200 4750
Wire Wire Line
	7100 4650 7100 4750
Connection ~ 7100 4750
Wire Wire Line
	7000 4650 7000 4750
Connection ~ 7000 4750
Wire Wire Line
	6900 4650 6900 4750
Connection ~ 6900 4750
Wire Wire Line
	6800 4650 6800 4750
Connection ~ 6800 4750
Wire Wire Line
	6700 4650 6700 4750
Connection ~ 6700 4750
Connection ~ 7300 4750
Wire Wire Line
	1450 4250 1350 4250
Wire Wire Line
	1350 4250 1350 4900
Wire Wire Line
	1450 4350 1350 4350
Connection ~ 1350 4350
Wire Wire Line
	1450 4450 1350 4450
Connection ~ 1350 4450
Wire Wire Line
	1450 4550 1350 4550
Connection ~ 1350 4550
Wire Wire Line
	1450 4650 1350 4650
Connection ~ 1350 4650
Wire Wire Line
	1350 4050 1450 4050
Wire Wire Line
	1350 3800 1350 4050
Wire Wire Line
	1450 3950 1350 3950
Connection ~ 1350 3950
Wire Wire Line
	1450 3850 1350 3850
Connection ~ 1350 3850
Wire Wire Line
	3450 4550 4100 4550
Wire Wire Line
	4100 4550 4100 4800
Wire Wire Line
	3450 4450 4200 4450
Wire Wire Line
	4200 4450 4200 4800
Wire Wire Line
	3450 4350 4300 4350
Wire Wire Line
	4300 4350 4300 4800
Wire Wire Line
	3450 4250 4400 4250
Wire Wire Line
	4400 4250 4400 4800
Wire Wire Line
	3450 4150 4500 4150
Wire Wire Line
	4500 4150 4500 4800
Wire Wire Line
	3450 4050 4600 4050
Wire Wire Line
	4600 4050 4600 4800
Wire Wire Line
	3450 3950 4700 3950
Wire Wire Line
	4700 3950 4700 4800
NoConn ~ 4700 5300
NoConn ~ 4400 5300
$Comp
L +3.3V #PWR04
U 1 1 59FFA707
P 4700 5500
F 0 "#PWR04" H 4700 5460 30  0001 C CNN
F 1 "+3.3V" H 4700 5610 30  0000 C CNN
F 2 "" H 4700 5500 60  0001 C CNN
F 3 "" H 4700 5500 60  0001 C CNN
	1    4700 5500
	1    0    0    -1  
$EndComp
Wire Wire Line
	4700 5550 4700 5500
Wire Wire Line
	4500 5550 4700 5550
Wire Wire Line
	4500 5550 4500 5300
Wire Wire Line
	4600 5300 4600 5550
Connection ~ 4600 5550
Wire Wire Line
	1450 3650 1150 3650
Wire Wire Line
	1150 3650 1150 2800
Wire Wire Line
	1150 2800 4800 2800
Wire Wire Line
	4800 2800 4800 4800
Wire Wire Line
	1450 3450 1250 3450
Wire Wire Line
	1250 3450 1250 2700
Wire Wire Line
	1250 2700 4900 2700
Wire Wire Line
	4900 2700 4900 4800
Wire Wire Line
	5000 4800 5000 2600
Wire Wire Line
	5000 2600 1350 2600
Wire Wire Line
	1350 2600 1350 3250
Wire Wire Line
	1350 3250 1450 3250
NoConn ~ 4900 5300
NoConn ~ 5000 5300
$Comp
L LED_Small D1
U 1 1 59FFAACD
P 4600 6150
F 0 "D1" H 4550 6275 50  0000 L CNN
F 1 "LED_Small" H 4425 6050 50  0000 L CNN
F 2 "LEDs:LED_0805" V 4600 6150 50  0001 C CNN
F 3 "" V 4600 6150 50  0001 C CNN
	1    4600 6150
	-1   0    0    -1  
$EndComp
$Comp
L LED_Small D2
U 1 1 59FFAAFB
P 4600 6500
F 0 "D2" H 4550 6625 50  0000 L CNN
F 1 "LED_Small" H 4425 6400 50  0000 L CNN
F 2 "LEDs:LED_0805" V 4600 6500 50  0001 C CNN
F 3 "" V 4600 6500 50  0001 C CNN
	1    4600 6500
	-1   0    0    -1  
$EndComp
$Comp
L LED_Small D3
U 1 1 59FFAB35
P 4600 6850
F 0 "D3" H 4550 6975 50  0000 L CNN
F 1 "LED_Small" H 4425 6750 50  0000 L CNN
F 2 "LEDs:LED_0805" V 4600 6850 50  0001 C CNN
F 3 "" V 4600 6850 50  0001 C CNN
	1    4600 6850
	-1   0    0    -1  
$EndComp
Wire Wire Line
	4300 5300 4300 5800
Wire Wire Line
	4300 5800 4500 5800
Wire Wire Line
	4200 5300 4200 6150
Wire Wire Line
	4200 6150 4500 6150
Wire Wire Line
	4100 5300 4100 6500
Wire Wire Line
	4100 6500 4500 6500
Wire Wire Line
	4000 5300 4000 6850
Wire Wire Line
	4000 6850 4500 6850
$Comp
L R R0
U 1 1 59FFACCF
P 5050 5800
F 0 "R0" V 5130 5800 50  0000 C CNN
F 1 "R" V 5050 5800 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 4980 5800 50  0001 C CNN
F 3 "" H 5050 5800 50  0001 C CNN
	1    5050 5800
	0    -1   -1   0   
$EndComp
$Comp
L R R1
U 1 1 59FFADB0
P 5050 6150
F 0 "R1" V 5130 6150 50  0000 C CNN
F 1 "R" V 5050 6150 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 4980 6150 50  0001 C CNN
F 3 "" H 5050 6150 50  0001 C CNN
	1    5050 6150
	0    -1   -1   0   
$EndComp
$Comp
L R R2
U 1 1 59FFADE5
P 5050 6500
F 0 "R2" V 5130 6500 50  0000 C CNN
F 1 "R" V 5050 6500 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 4980 6500 50  0001 C CNN
F 3 "" H 5050 6500 50  0001 C CNN
	1    5050 6500
	0    -1   -1   0   
$EndComp
$Comp
L R R3
U 1 1 59FFAE21
P 5050 6850
F 0 "R3" V 5130 6850 50  0000 C CNN
F 1 "R" V 5050 6850 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 4980 6850 50  0001 C CNN
F 3 "" H 5050 6850 50  0001 C CNN
	1    5050 6850
	0    -1   -1   0   
$EndComp
Wire Wire Line
	4700 5800 4900 5800
Wire Wire Line
	4700 6150 4900 6150
Wire Wire Line
	4700 6500 4900 6500
Wire Wire Line
	4700 6850 4900 6850
$Comp
L GND #PWR05
U 1 1 59FFAFF1
P 5400 7100
F 0 "#PWR05" H 5400 7100 30  0001 C CNN
F 1 "GND" H 5400 7030 30  0001 C CNN
F 2 "" H 5400 7100 60  0001 C CNN
F 3 "" H 5400 7100 60  0001 C CNN
	1    5400 7100
	1    0    0    -1  
$EndComp
Wire Wire Line
	5400 6850 5200 6850
Wire Wire Line
	5400 5800 5400 7100
Wire Wire Line
	5200 6500 5400 6500
Connection ~ 5400 6850
Wire Wire Line
	5200 6150 5400 6150
Connection ~ 5400 6500
Wire Wire Line
	5200 5800 5400 5800
Connection ~ 5400 6150
Text Label 3500 3950 0    60   ~ 0
GPIO7
Text Label 3500 4050 0    60   ~ 0
SPIPHA
Text Label 3500 4150 0    60   ~ 0
SPIPOL
Text Label 3500 4250 0    60   ~ 0
GPIO4
Text Label 3500 4350 0    60   ~ 0
TXLED
Text Label 3500 4450 0    60   ~ 0
RXLED
Text Label 3500 4550 0    60   ~ 0
SFDLED
Text Label 3500 4650 0    60   ~ 0
RXOKLED
Wire Wire Line
	3450 4650 4000 4650
Wire Wire Line
	4000 4650 4000 4800
Text Label 3500 2800 0    60   ~ 0
RSTn
Text Label 3500 2700 0    60   ~ 0
WAKEUP
Text Label 3500 2600 0    60   ~ 0
EXTON
NoConn ~ 6000 3750
NoConn ~ 6000 3850
NoConn ~ 6000 4050
NoConn ~ 6000 4150
NoConn ~ 6000 3150
NoConn ~ 6000 2950
NoConn ~ 6000 2850
NoConn ~ 6000 2650
NoConn ~ 6000 2550
NoConn ~ 6000 2450
NoConn ~ 7800 2650
NoConn ~ 7800 2750
NoConn ~ 7800 2850
NoConn ~ 7800 2950
NoConn ~ 7800 3050
NoConn ~ 7800 3150
NoConn ~ 7800 3250
NoConn ~ 7800 3350
NoConn ~ 7800 3650
NoConn ~ 7800 3750
$Comp
L 24LC128 U1
U 1 1 59FFC389
P 9450 4150
F 0 "U1" H 9200 4400 50  0000 C CNN
F 1 "24LC128" H 9650 4400 50  0001 C CNN
F 2 "Housings_SOIC:SOIC-8_3.9x4.9mm_Pitch1.27mm" H 9500 3900 50  0001 L CNN
F 3 "" H 9450 4050 50  0001 C CNN
	1    9450 4150
	-1   0    0    -1  
$EndComp
Wire Wire Line
	7800 4050 9050 4050
Wire Wire Line
	7800 4150 9050 4150
$Comp
L R R4
U 1 1 59FFC647
P 8550 3650
F 0 "R4" V 8500 3500 50  0000 C CNN
F 1 "3K9" V 8550 3650 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 8480 3650 50  0001 C CNN
F 3 "" H 8550 3650 50  0001 C CNN
	1    8550 3650
	1    0    0    -1  
$EndComp
$Comp
L R R5
U 1 1 59FFC6EA
P 8650 3650
F 0 "R5" V 8600 3500 50  0000 C CNN
F 1 "3K9" V 8650 3650 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 8580 3650 50  0001 C CNN
F 3 "" H 8650 3650 50  0001 C CNN
	1    8650 3650
	1    0    0    -1  
$EndComp
Wire Wire Line
	8550 3800 8550 4050
Connection ~ 8550 4050
Wire Wire Line
	8650 3800 8650 4150
Connection ~ 8650 4150
$Comp
L R R6
U 1 1 59FFC936
P 8750 3650
F 0 "R6" V 8700 3500 50  0000 C CNN
F 1 "3K9" V 8750 3650 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 8680 3650 50  0001 C CNN
F 3 "" H 8750 3650 50  0001 C CNN
	1    8750 3650
	1    0    0    -1  
$EndComp
Wire Wire Line
	8750 3800 8750 4500
Wire Wire Line
	8750 4250 9050 4250
$Comp
L +3.3V #PWR06
U 1 1 59FFCA2C
P 9450 3150
F 0 "#PWR06" H 9450 3110 30  0001 C CNN
F 1 "+3.3V" H 9450 3260 30  0000 C CNN
F 2 "" H 9450 3150 60  0001 C CNN
F 3 "" H 9450 3150 60  0001 C CNN
	1    9450 3150
	1    0    0    -1  
$EndComp
Wire Wire Line
	9450 3150 9450 3850
Connection ~ 9450 3300
Text Label 8850 4050 0    60   ~ 0
SDA
Text Label 8850 4150 0    60   ~ 0
SCL
Text Label 8850 4250 0    60   ~ 0
WP
$Comp
L CONN_01X02 J2
U 1 1 59FFD3FD
P 8550 4550
F 0 "J2" H 8550 4700 50  0000 C CNN
F 1 "CONN_01X02" V 8650 4550 50  0000 C CNN
F 2 "Pin_Headers:Pin_Header_Straight_1x02_Pitch2.54mm" H 8550 4550 50  0001 C CNN
F 3 "" H 8550 4550 50  0001 C CNN
	1    8550 4550
	-1   0    0    -1  
$EndComp
Connection ~ 8750 4250
$Comp
L CONN_02X03 J3
U 1 1 59FFD59F
P 10200 3650
F 0 "J3" H 10200 3850 50  0000 C CNN
F 1 "CONN_02X03" H 10200 3450 50  0000 C CNN
F 2 "Pin_Headers:Pin_Header_Straight_2x03_Pitch2.54mm" H 10200 2450 50  0001 C CNN
F 3 "" H 10200 2450 50  0001 C CNN
	1    10200 3650
	0    -1   -1   0   
$EndComp
$Comp
L R R7
U 1 1 59FFD61B
P 10100 4550
F 0 "R7" V 10050 4400 50  0000 C CNN
F 1 "3K9" V 10100 4550 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 10030 4550 50  0001 C CNN
F 3 "" H 10100 4550 50  0001 C CNN
	1    10100 4550
	1    0    0    -1  
$EndComp
$Comp
L R R8
U 1 1 59FFDBDF
P 10200 4550
F 0 "R8" V 10150 4400 50  0000 C CNN
F 1 "3K9" V 10200 4550 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 10130 4550 50  0001 C CNN
F 3 "" H 10200 4550 50  0001 C CNN
	1    10200 4550
	1    0    0    -1  
$EndComp
$Comp
L R R9
U 1 1 59FFDC2C
P 10300 4550
F 0 "R9" V 10250 4400 50  0000 C CNN
F 1 "3K9" V 10300 4550 50  0000 C CNN
F 2 "Resistors_SMD:R_0805" V 10230 4550 50  0001 C CNN
F 3 "" H 10300 4550 50  0001 C CNN
	1    10300 4550
	1    0    0    -1  
$EndComp
Wire Wire Line
	10300 4900 10300 4700
Wire Wire Line
	8750 4900 10300 4900
Wire Wire Line
	10200 4900 10200 4700
Wire Wire Line
	10100 4900 10100 4700
Connection ~ 10200 4900
Wire Wire Line
	9450 4450 9450 5050
Connection ~ 10100 4900
$Comp
L GND #PWR07
U 1 1 59FFE150
P 9450 5050
F 0 "#PWR07" H 9450 5050 30  0001 C CNN
F 1 "GND" H 9450 4980 30  0001 C CNN
F 2 "" H 9450 5050 60  0001 C CNN
F 3 "" H 9450 5050 60  0001 C CNN
	1    9450 5050
	1    0    0    -1  
$EndComp
Connection ~ 9450 4900
Wire Wire Line
	8750 4600 8750 4900
Wire Wire Line
	9850 4250 10100 4250
Wire Wire Line
	10100 3900 10100 4400
Connection ~ 10100 4250
Wire Wire Line
	9850 4150 10200 4150
Wire Wire Line
	10200 3900 10200 4400
Connection ~ 10200 4150
Wire Wire Line
	10300 3900 10300 4400
Connection ~ 10300 4050
Wire Wire Line
	8750 3300 8750 3500
Wire Wire Line
	8550 3300 10300 3300
Wire Wire Line
	8650 3500 8650 3300
Connection ~ 8750 3300
Wire Wire Line
	8550 3500 8550 3300
Connection ~ 8650 3300
Wire Wire Line
	10100 3300 10100 3400
Wire Wire Line
	10200 3300 10200 3400
Connection ~ 10100 3300
Wire Wire Line
	10300 3300 10300 3400
Connection ~ 10200 3300
Text Label 9900 4050 0    60   ~ 0
A0
Text Label 9900 4150 0    60   ~ 0
A1
Text Label 9900 4250 0    60   ~ 0
A2
Wire Wire Line
	10300 4050 9850 4050
NoConn ~ 7000 2050
NoConn ~ 7100 2050
$Comp
L +3.3V #PWR08
U 1 1 5A000900
P 6700 1850
F 0 "#PWR08" H 6700 1810 30  0001 C CNN
F 1 "+3.3V" H 6700 1960 30  0000 C CNN
F 2 "" H 6700 1850 60  0001 C CNN
F 3 "" H 6700 1850 60  0001 C CNN
	1    6700 1850
	1    0    0    -1  
$EndComp
Wire Wire Line
	6700 1850 6700 2050
Wire Wire Line
	6800 2050 6800 1950
Wire Wire Line
	6800 1950 6700 1950
Connection ~ 6700 1950
Wire Wire Line
	5100 4800 5100 3750
Wire Wire Line
	5100 3750 3450 3750
Wire Wire Line
	4800 5300 4800 5550
Wire Wire Line
	4800 5550 8150 5550
Wire Wire Line
	7800 3450 8150 3450
Wire Wire Line
	7800 3550 8050 3550
Wire Wire Line
	8050 3550 8050 5450
Wire Wire Line
	8050 5450 5100 5450
Wire Wire Line
	5100 5450 5100 5300
Text Label 6100 5550 0    60   ~ 0
RSTXn
Text Label 6100 5450 0    60   ~ 0
IRQX
$Comp
L CONN_02X12 J1
U 1 1 5A00C401
P 4550 5050
F 0 "J1" H 4550 5700 50  0000 C CNN
F 1 "CONN_02X12" V 4550 5050 50  0000 C CNN
F 2 "Pin_Headers:Pin_Header_Straight_2x12_Pitch2.54mm" H 4550 3850 50  0001 C CNN
F 3 "" H 4550 3850 50  0001 C CNN
	1    4550 5050
	0    -1   1    0   
$EndComp
$EndSCHEMATC
