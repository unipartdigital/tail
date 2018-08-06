# -*- python -*-
#
# Tail configuration file
#

RPC_PORT = 61666

C_ABS = 299792458
C_AIR = 299705000

DW_CLOCK_GHZ = 63.8976


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
    'tx_power'        : 0x00d1d100,
    'xtalt'	      : 15,
    'antd'            : 0x4020,
    'snr_threshold'   : 1,
    'fpr_threshold'   : 1,
    'noise_threshold' : 4096,
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
        'xtalt'	   : 16,
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
        'xtalt'	   : 17,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000012': {
        'xtalt'	   : 23,		# Unstable
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000013': {
        'xtalt'	   : 16,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000014': {
        'xtalt'	   : 17,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000015': {
        'xtalt'	   : 15,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000016': {
        'xtalt'	   : 18,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000017': {
        'xtalt'	   : 16,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000018': {
        'xtalt'	   : 15,
        'antd'     : 0x401f,
    },
    '70b3d5b1e0000019': {
        'xtalt'	   : 16,
        'antd'     : 0x401f,
    },
}
        

