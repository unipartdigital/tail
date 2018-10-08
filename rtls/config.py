# -*- python -*-
#
# Tail configuration file
#

RPC_PORT = 61666

C_ABS = 299792458
C_AIR = 299705000

DW1000_CLOCK_GHZ = 63.8976
DW1000_CLOCK_HZ  = DW1000_CLOCK_GHZ * 1E9

DW1000_64PRF_ANTD_NS = 514.4620
DW1000_16PRF_ANTD_NS = 513.9067

DW1000_64PRF_ANTD_DEFAULT = int(DW1000_64PRF_ANTD_NS * DW1000_CLOCK_GHZ / 2)
DW1000_16PRF_ANTD_DEFAULT = int(DW1000_16PRF_ANTD_NS * DW1000_CLOCK_GHZ / 2)

DW1000_RX_POWER_TABLE = (
    (0, 0, 0, 0),
    (25, 25, 25, 25),
    (65, 65, 65, 65),
    (105, 105, 105, 105),
    (145, 145, 145, 145),
    (185, 185, 185, 185),
    (225, 225, 225, 225),
    (265, 265, 265, 265),
    (305, 305, 303, 305),
    (345, 345, 342, 345),
    (385, 385, 382, 385),
    (425, 420, 422, 425),
    (465, 460, 466, 465),
    (505, 502, 506, 505),
    (545, 542, 546, 545),
    (585, 576, 578, 576),
    (625, 612, 606, 622),
    (665, 644, 630, 658),
    (705, 668, 670, 695),
    (745, 686, 706, 730),
    (785, 710, 738, 765),
    (825, 716, 774, 795),
    (865, 735, 802, 810),
    (905, 752, 846, 840),
    (945, 763, 878, 865),
    (985, 775, 898, 888),
    (1025, 784, 921, 908),
    (1065, 796, 938, 928),
    (1105, 808, 954, 948),
    (1145, 816, 961, 966),
    (1185, 831, 975, 980),
    (1225, 843, 986, 1004),
    (1265, 854, 990, 1024),
    (1305, 866, 997, 1050),
    (1345, 883, 1006, 1070),
    (1385, 895, 1010, 1086),
    (1425, 904, 1018, 1098),
    (1465, 915, 1022, 1110),
    (1505, 924, 1026, 1118),
    (1545, 934, 1030, 1128),
    (1585, 944, 1034, 1140),
)


DW1000_TSINFO_ATTRS = (
    'rawts',
    'lqi',
    'snr',
    'fpr',
    'noise',
    'rxpacc',
    'fp_index',
    'fp_ampl1',
    'fp_ampl2',
    'fp_ampl3',
    'cir_pwr',
    'fp_pwr',
    'ttcko',
    'ttcki',
)


DW1000_DEFAULT_CONFIG = {
    'channel'	      : 7,
    'pcode'	      : 20,
    'prf'	      : 64,
    'rate'	      : 6800,
    'txpsr'	      : 256,
    'smart_power'     : 0,
    'tx_power'        : 0xd1d1d1d1,
    'xtalt'	      : 15,
    'antd'            : DW1000_64PRF_ANTD_DEFAULT,
    'snr_threshold'   : 0,
    'fpr_threshold'   : 0,
    'noise_threshold' : 65535,
}

DW1000_CALIB_CONFIG = {
    'channel'	      : 7,
    'pcode'	      : 20,
    'prf'	      : 64,
    'rate'	      : 850,
    'txpsr'	      : 1024,
    'smart_power'     : 0,
    'tx_power'        : 0xb1b1b1b1,
    'snr_threshold'   : 0,
    'fpr_threshold'   : 0,
    'noise_threshold' : 65535,
}

DW1000_DEVICE_CALIB = {
    '70b3d5b1e0000001': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000002': {
        'xtalt'	   : 17,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000003': {
        'xtalt'	   : 17,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000004': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000005': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000006': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000007': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000008': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000009': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e000000a': {
        'xtalt'	   : 17,
        'antd'     : 0x403b,
    },
    '70b3d5b1e000000b': {
        'xtalt'	   : 18,
        'antd'     : 0x403b,
    },
    '70b3d5b1e000000c': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e000000d': {
        'xtalt'	   : 15,
        'antd'     : 0x4018,
    },
    '70b3d5b1e000000e': {
        'xtalt'	   : 17,
        'antd'     : 0x403b,
    },
    '70b3d5b1e000000f': {
        'xtalt'	   : 16,
        'antd'     : 0x403b,
    },
    '70b3d5b1e0000010': {
        'xtalt'	   : 18,
        'antd'     : 0x4010,
    },
    '70b3d5b1e0000011': {
        'bss'      : 4,
        'host'     : 'bss5',
        'xtalt'	   : 17,
        'antd'     : 0x401e,
        'coord'    : (2.666, 0.185, 1.255),
    },
    '70b3d5b1e0000012': {
        'xtalt'	   : 23,		# Unstable
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000013': {
        'bss'      : 5,
        'host'     : 'bss6',
        'xtalt'	   : 16,
        'antd'     : 0x402f,
        'coord'    : (6.177, 0.185, 1.255),
    },
    '70b3d5b1e0000014': {
        'bss'      : 0,
        'host'     : 'bss1',
        'xtalt'	   : 17,
        'antd'     : 0x4049,
        'coord'    : (0.150, 0.475, 0.035),
    },
    '70b3d5b1e0000015': {
        'bss'      : 1,
        'host'     : 'bss2',
        'xtalt'	   : 15,
        'antd'     : 0x4040,
        'coord'    : (8.545, 0.420, 0.035),
    },
    '70b3d5b1e0000016': {
        'bss'      : 2,
        'host'     : 'bss3',
        'xtalt'	   : 17,
        'antd'     : 0x404a,
        'coord'    : (8.567, 5.807, 0.035),
    },
    '70b3d5b1e0000017': {
        'bss'      : 3,
        'host'     : 'bss4',
        'xtalt'	   : 15,
        'antd'     : 0x4032,
        'coord'    : (0.175, 5.860, 0.035),
    },
    '70b3d5b1e0000018': {
        'bss'      : 6,
        'host'     : 'bss7',
        'xtalt'	   : 15,
        'antd'     : 0x4023,
        'coord'    : (6.102, 6.146, 1.265),
    },
    '70b3d5b1e0000019': {
        'bss'      : 7,
        'host'     : 'bss8',
        'xtalt'	   : 16,
        'antd'     : 0x4018,
        'coord'    : (2.299, 6.140, 1.270),
    },
    '70b3d5b1e0000020': {
        'xtalt'	   : 22,
        'antd'     : 0x401b,
    },
    '70b3d5b1e0000021': {
        'xtalt'	   : 22,
        'antd'     : 0x4015,
    },
    '70b3d5b1e0000022': {
        'xtalt'	   : 23,
        'antd'     : 0x4023,
    },
    '70b3d5b1e0000023': {
        'xtalt'	   : 23,
        'antd'     : 0x401e,
    },
}

