/* radio_reg.h */

#ifndef _RADIO_REG_H
#define _RADIO_REG_H

#define RREG(x)   RREG_(REG_##x)
#define RREG_(x)  RREG_PAIR(x)
#define RLEN(x)   RLEN_(REG_##x)
#define RLEN_(x)  RREG_LAST(x)

#define FSHIFT(field, offset) (FFIRST(FIELD_##field) - (offset*8))
#define FBITS(field)          FSECOND(FIELD_##field)
#define FMASK(field, offset)  (((1<<FBITS(field))-1)<<FSHIFT(field, offset))

#define FIELDO(field, offset, value) ((value) << (FSHIFT(field, offset)))
#define FIELDVALO(field, offset) (((value) >> (FSHIFT(field, offset)))) & ((1<<FBITS(field))-1))
#define FIELD(field, value) FIELDO(field, 0, value)
#define FIELDVAL(field) FIELDVALO(field, 0)

#define FLAG(field) (1 << FSHIFT(field, 0))

/* Register plus offset */
#define RREGO(x, o) RREG(x)+o

#define RREG_PAIR(x, y, z) x, y
#define RREG_LAST(x, y, z) z

#define FFIRST(x) FFIRST_(x)
#define FSECOND(x) FSECOND_(x)
#define FFIRST_(x, y) x
#define FSECOND_(x, y) y

#define NAME_COUNT2(x, ...) NAME_COUNT2_(x, COUNT2(__VA_ARGS__))
#define NAME_COUNT2_(x, n)  NAME_COUNT2__(x, n)
#define NAME_COUNT2__(x, n)  x ## n

#define FIELDS(reg, ...) FIELDSO(reg, 0, __VA_ARGS__)
#define FIELDSO(reg, offset, ...) ( NAME_COUNT2(FIELDS_, __VA_ARGS__) (reg, offset, __VA_ARGS__) )
#define FIELDS_1(reg, offset, field, value) FIELDO(reg##_##field, offset, value)
#define FIELDS_2(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_1(reg, offset, __VA_ARGS__)
#define FIELDS_3(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_2(reg, offset, __VA_ARGS__)
#define FIELDS_4(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_3(reg, offset, __VA_ARGS__)
#define FIELDS_5(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_4(reg, offset, __VA_ARGS__)
#define FIELDS_6(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_5(reg, offset, __VA_ARGS__)
#define FIELDS_7(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_6(reg, offset, __VA_ARGS__)
#define FIELDS_8(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_7(reg, offset, __VA_ARGS__)
#define FIELDS_9(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_8(reg, offset, __VA_ARGS__)
#define FIELDS_10(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_9(reg, offset, __VA_ARGS__)
#define FIELDS_11(reg, offset, field, value, ...) FIELDO(reg##_##field, offset, value) | FIELDS_10(reg, offset, __VA_ARGS__)
#define FIELDS_12(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_11(reg, offset, __VA_ARGS__)
#define FIELDS_13(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_12(reg, offset, __VA_ARGS__)
#define FIELDS_14(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_13(reg, offset, __VA_ARGS__)
#define FIELDS_15(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_14(reg, offset, __VA_ARGS__)
#define FIELDS_16(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_15(reg, offset, __VA_ARGS__)
#define FIELDS_17(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_16(reg, offset, __VA_ARGS__)
#define FIELDS_18(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_17(reg, offset, __VA_ARGS__)
#define FIELDS_19(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_18(reg, offset, __VA_ARGS__)
#define FIELDS_20(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_19(reg, offset, __VA_ARGS__)
#define FIELDS_21(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_20(reg, offset, __VA_ARGS__)
#define FIELDS_22(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_21(reg, offset, __VA_ARGS__)
#define FIELDS_23(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_22(reg, offset, __VA_ARGS__)
#define FIELDS_24(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_23(reg, offset, __VA_ARGS__)
#define FIELDS_25(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_24(reg, offset, __VA_ARGS__)
#define FIELDS_26(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_25(reg, offset, __VA_ARGS__)
#define FIELDS_27(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_26(reg, offset, __VA_ARGS__)
#define FIELDS_28(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_27(reg, offset, __VA_ARGS__)
#define FIELDS_29(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_28(reg, offset, __VA_ARGS__)
#define FIELDS_30(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_29(reg, offset, __VA_ARGS__)
#define FIELDS_31(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_30(reg, offset, __VA_ARGS__)
#define FIELDS_32(reg, offset, field, value, ...) FIELDO(reg##_##offset, field, value) | FIELDS_31(reg, offset, __VA_ARGS__)

#define FIELDS_MASK(reg, ...) FIELDS_MASKO(reg, 0, __VA_ARGS__)
#define FIELDS_MASKO(reg, offset, ...) ( NAME_COUNT2(FIELDS_MASK_, __VA_ARGS__) (reg, offset, __VA_ARGS__) )
#define FIELDS_MASK_1(reg, offset, field, value) FMASK(reg##_##field, offset)
#define FIELDS_MASK_2(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_1(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_3(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_2(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_4(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_3(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_5(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_4(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_6(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_5(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_7(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_6(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_8(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_7(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_9(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_8(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_10(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_9(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_11(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_10(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_12(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_11(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_13(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_12(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_14(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_13(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_15(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_14(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_16(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_15(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_17(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_16(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_18(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_17(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_19(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_18(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_20(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_19(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_21(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_20(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_22(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_21(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_23(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_22(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_24(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_23(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_25(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_24(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_26(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_25(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_27(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_26(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_28(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_27(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_29(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_28(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_30(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_29(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_31(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_30(reg, offset, __VA_ARGS__)
#define FIELDS_MASK_32(reg, offset, field, value, ...) FMASK(reg##_##field, offset) | FIELDS_MASK_31(reg, offset, __VA_ARGS__)


#define FIELDS_EDIT(var, ...) var = (((var) & ~FIELDS_MASK(__VA_ARGS__)) | FIELDS(__VA_ARGS__))
#define FIELDS_EDITO(var, ...) var = (((var) & ~FIELDS_MASKO(__VA_ARGS__)) | FIELDSO(__VA_ARGS__))


#define COUNT2(...) _COUNT2(__VA_ARGS__, 32,32,31,31,30,30,29,29,28,28,27,27,26,26,25,25,24,24,23,23,22,22,21,21,20,20,19,19,18,18,17,17,16,16,15,15,14,14,13,13,12,12,11,11,10,10,9,9,8,8,7,7,6,6,5,5,4,4,3,3,2,2,1,1,end)
#define _COUNT2(_1,_2,_3,_4,_5,_6,_7,_8,_9,_10,_11,_12,_13,_14,_15,_16,_17,_18,_19,_20,_21,_22,_23,_24,_25,_26,_27,_28,_29,_30,_31,_32,_33,_34,_35,_36,_37,_38,_39,_40,_41,_42,_43,_44,_45,_46,_47,_48,_49,_50,_51,_52,_53,_54,_55,_56,_57,_58,_59,_60,_61,_62,_63,_64,n,...) n



#define FILE_DEV_ID     0x00
#define FILE_EUI        0x01
#define FILE_PANADR     0x03
#define FILE_SYS_CFG    0x04
#define FILE_SYS_TIME   0x06
#define FILE_TX_FCTRL   0x08
#define FILE_TX_BUFFER  0x09
#define FILE_DX_TIME    0x0A
#define FILE_RX_FWTO    0x0C
#define FILE_SYS_CTRL   0x0D
#define FILE_SYS_MASK   0x0E
#define FILE_SYS_STATUS 0x0F
#define FILE_RX_FINFO   0x10
#define FILE_RX_BUFFER  0x11
#define FILE_RX_FQUAL   0x12
#define FILE_RX_TTCKI   0x13
#define FILE_RX_TTCKO   0x14
#define FILE_RX_TIME    0x15
#define FILE_TX_TIME    0x17
#define FILE_TX_ANTD    0x18
#define FILE_SYS_STATE  0x19
#define FILE_ACK_RESP_T 0x1A
#define FILE_RX_SNIFF   0x1D
#define FILE_TX_POWER   0x1E
#define FILE_CHAN_CTRL  0x1F
#define FILE_USR_SFD    0x21
#define FILE_AGC_CTRL   0x23
#define FILE_EXT_SYNC   0x24
#define FILE_ACC_MEM    0x25
#define FILE_GPIO_CTRL  0x26
#define FILE_DRX_CONF   0x27
#define FILE_RF_CONF    0x28
#define FILE_TX_CAL     0x2A
#define FILE_FS_CTRL    0x2B
#define FILE_AON        0x2C
#define FILE_OTP_IF     0x2D
#define FILE_LDE_CTRL   0x2E
#define FILE_DIG_DIAG   0x2F
#define FILE_PMSC       0x36
 
#define REG_DEV_ID      FILE_DEV_ID,     0x00, 4
#define REG_EUI         FILE_EUI,        0x00, 0
#define REG_PANADR      FILE_PANADR,     0x00, 4
#define REG_SYS_CFG     FILE_SYS_CFG,    0x00, 4
#define REG_SYS_TIME    FILE_SYS_TIME,   0x00, 5
#define REG_TX_FCTRL    FILE_TX_FCTRL,   0x00, 5
#define REG_TX_BUFFER   FILE_TX_BUFFER,  0x00, 1024
#define REG_DX_TIME     FILE_DX_TIME,    0x00, 5
#define REG_RX_FWTO     FILE_RX_FWTO,    0x00, 2
#define REG_SYS_CTRL    FILE_SYS_CTRL,   0x00, 4
#define REG_SYS_MASK    FILE_SYS_MASK,   0x00, 4
#define REG_SYS_STATUS  FILE_SYS_STATUS, 0x00, 5
#define REG_RX_FINFO    FILE_RX_FINFO,   0x00, 4
#define REG_RX_BUFFER   FILE_RX_BUFFER,  0x00, 1024
#define REG_RX_FQUAL    FILE_RX_FQUAL,   0x00, 8
#define REG_RX_TTCKI    FILE_RX_TTCKI,   0x00, 4
#define REG_RX_TTCKO    FILE_RX_TTCKO,   0x00, 5
#define REG_RX_TIME     FILE_RX_TIME,    0x00, 14
#define REG_TX_TIME     FILE_TX_TIME,    0x00, 10
#define REG_TX_ANTD     FILE_TX_ANTD,    0x00, 2
#define REG_SYS_STATE   FILE_SYS_STATE,  0x00, 5
#define REG_ACK_RESP_T  FILE_ACK_RESP_T, 0x00, 4
#define REG_RX_SNIFF    FILE_RX_SNIFF,   0x00, 4
#define REG_TX_POWER    FILE_TX_POWER,   0x00, 4
#define REG_CHAN_CTRL   FILE_CHAN_CTRL,  0x00, 4
#define REG_USR_SFD     FILE_USR_SFD,    0x00, 41
#define REG_AGC_RES1    FILE_AGC_CTRL,   0x00, 2
#define REG_AGC_CTRL1   FILE_AGC_CTRL,   0x02, 2
#define REG_AGC_TUNE1   FILE_AGC_CTRL,   0x04, 2
#define REG_AGC_RES2    FILE_AGC_CTRL,   0x06, 6
#define REG_AGC_TUNE2   FILE_AGC_CTRL,   0x0C, 4
#define REG_AGC_RES3    FILE_AGC_CTRL,   0x10, 2
#define REG_AGC_TUNE3   FILE_AGC_CTRL,   0x12, 2
#define REG_AGC_RES4    FILE_AGC_CTRL,   0x14, 10
#define REG_AGC_STAT1   FILE_AGC_CTRL,   0x1E, 3
#define REG_EC_CTRL     FILE_EXT_SYNC,   0x00, 4
#define REG_EC_RXTC     FILE_EXT_SYNC,   0x04, 4
#define REG_EC_GOLP     FILE_EXT_SYNC,   0x08, 4
/* ACC_MEM requires the first octet to be discarded - see datasheet */
#define REG_ACC_MEM     FILE_ACC_MEM,    0x00, 4064
#define REG_GPIO_MODE   FILE_GPIO_CTRL,  0x00, 4
#define REG_GPIO_DIR    FILE_GPIO_CTRL,  0x08, 4
#define REG_GPIO_DOUT   FILE_GPIO_CTRL,  0x0C, 4
#define REG_GPIO_IRQE   FILE_GPIO_CTRL,  0x10, 4
#define REG_GPIO_ISEN   FILE_GPIO_CTRL,  0x14, 4
#define REG_GPIO_IMODE  FILE_GPIO_CTRL,  0x18, 4
#define REG_GPIO_IBES   FILE_GPIO_CTRL,  0x1C, 4
#define REG_GPIO_ICLR   FILE_GPIO_CTRL,  0x20, 4
#define REG_GPIO_IDBE   FILE_GPIO_CTRL,  0x24, 4
#define REG_GPIO_RAW    FILE_GPIO_CTRL,  0x28, 4
#define REG_DRX_TUNE0B  FILE_DRX_CONF,   0x02, 2
#define REG_DRX_TUNE1A  FILE_DRX_CONF,   0x04, 2
#define REG_DRX_TUNE1B  FILE_DRX_CONF,   0x06, 2
#define REG_DRX_TUNE2   FILE_DRX_CONF,   0x08, 4
#define REG_DRX_SFDTOC  FILE_DRX_CONF,   0x20, 2
#define REG_DRX_PRETOC  FILE_DRX_CONF,   0x24, 2
#define REG_DRX_TUNE4H  FILE_DRX_CONF,   0x26, 2
#define REG_RF_CONF     FILE_RF_CONF,    0x00, 4
#define REG_RF_RES1     FILE_RF_CONF,    0x04, 7
#define REG_RF_RXCTRLH  FILE_RF_CONF,    0x0B, 1
#define REG_RF_TXCTRL   FILE_RF_CONF,    0x0C, 4
#define REG_RF_RES2     FILE_RF_CONF,    0x10, 16
#define REG_RF_STATUS   FILE_RF_CONF,    0x2C, 4
#define REG_RF_LDOTUNE  FILE_RF_CONF,    0x30, 4
#define REG_TC_SARC     FILE_TX_CAL,     0x00, 2
#define REG_TC_SARL     FILE_TX_CAL,     0x03, 1
#define REG_TC_SARW     FILE_TX_CAL,     0x06, 2
#define REG_TC_PGDELAY  FILE_TX_CAL,     0x0B, 1
#define REG_TC_PGTEST   FILE_TX_CAL,     0x0C, 1
#define REG_FS_PLLCFG   FILE_FS_CTRL,    0x07, 4
#define REG_FS_PLLTUNE  FILE_FS_CTRL,    0x0B, 1
#define REG_FS_XTALT    FILE_FS_CTRL,    0x0E, 1
#define REG_AON_WCFG    FILE_AON,        0x00, 2
#define REG_AON_CTRL    FILE_AON,        0x02, 1
#define REG_AON_RDAT    FILE_AON,        0x03, 1
#define REG_AON_ADDR    FILE_AON,        0x04, 1
#define REG_AON_CFG0    FILE_AON,        0x06, 4
#define REG_AON_CFG1    FILE_AON,        0x0A, 2
#define REG_OTP_WDAT    FILE_OTP_IF,     0x00, 4
#define REG_OTP_ADDR    FILE_OTP_IF,     0x04, 2
#define REG_OTP_CTRL    FILE_OTP_IF,     0x06, 2
#define REG_OTP_STAT    FILE_OTP_IF,     0x08, 2
#define REG_OTP_RDAT    FILE_OTP_IF,     0x0A, 4
#define REG_OTP_SRDAT   FILE_OTP_IF,     0x0E, 4
#define REG_OTP_SF      FILE_OTP_IF,     0x12, 1
#define REG_LDE_THRESH  FILE_LDE_CTRL,   0x0000, 2
#define REG_LDE_CFG1    FILE_LDE_CTRL,   0x0806, 1
#define REG_LDE_PPINDX  FILE_LDE_CTRL,   0x1000, 2
#define REG_LDE_PPAMPL  FILE_LDE_CTRL,   0x1002, 2
#define REG_LDE_RXANTD  FILE_LDE_CTRL,   0x1804, 2
#define REG_LDE_CFG2    FILE_LDE_CTRL,   0x1806, 2
#define REG_LDE_REPC    FILE_LDE_CTRL,   0x2804, 2
#define REG_EVC_CTRL    FILE_DIG_DIAG,   0x00, 4
#define REG_EVC_PHE     FILE_DIG_DIAG,   0x04, 2
#define REG_EVC_RSE     FILE_DIG_DIAG,   0x06, 2
#define REG_EVC_FCG     FILE_DIG_DIAG,   0x08, 2
#define REG_EVC_FCE     FILE_DIG_DIAG,   0x0A, 2
#define REG_EVC_FFR     FILE_DIG_DIAG,   0x0C, 2
#define REG_EVC_OVR     FILE_DIG_DIAG,   0x0E, 2
#define REG_EVC_STO     FILE_DIG_DIAG,   0x10, 2
#define REG_EVC_PTO     FILE_DIG_DIAG,   0x12, 2
#define REG_EVC_FWTO    FILE_DIG_DIAG,   0x14, 2
#define REG_EVC_TXFS    FILE_DIG_DIAG,   0x16, 2
#define REG_EVC_HPW     FILE_DIG_DIAG,   0x18, 2
#define REG_EVC_TPW     FILE_DIG_DIAG,   0x1A, 2
#define REG_EVC_TMC     FILE_DIG_DIAG,   0x24, 2
#define REG_PMSC_CTRL0  FILE_PMSC,       0x00, 4
#define REG_PMSC_CTRL1  FILE_PMSC,       0x04, 4
#define REG_PMSC_SNOZT  FILE_PMSC,       0x0C, 1
#define REG_PMSC_TXFSEQ FILE_PMSC,       0x26, 2
#define REG_PMSC_LEDC   FILE_PMSC,       0x28, 4

#define FIELD_DEV_ID_REG          0,  4
#define FIELD_DEV_ID_VER          4,  4
#define FIELD_DEV_ID_MODEL        8,  8
#define FIELD_DEV_ID_RIDTAG      16, 16

#define FIELD_PANADR_SHORT_ADDR   0, 16
#define FIELD_PANADR_PAN_ID      16, 16

#define FIELD_SYS_CFG_FFEN        0,  1
#define FIELD_SYS_CFG_FFBC        1,  1
#define FIELD_SYS_CFG_FFAB        2,  1
#define FIELD_SYS_CFG_FFAD        3,  1
#define FIELD_SYS_CFG_FFAA        4,  1
#define FIELD_SYS_CFG_FFAM        5,  1
#define FIELD_SYS_CFG_FFAR        6,  1
#define FIELD_SYS_CFG_FFA4        7,  1
#define FIELD_SYS_CFG_FFA5        8,  1
#define FIELD_SYS_CFG_HIRQ_POL    9,  1
#define FIELD_SYS_CFG_SPI_EDGE   10,  1
#define FIELD_SYS_CFG_DIS_FCE    11,  1
#define FIELD_SYS_CFG_DIS_DRXB   12,  1
#define FIELD_SYS_CFG_DIS_PHE    13,  1
#define FIELD_SYS_CFG_DIS_RSDE   14,  1
#define FIELD_SYS_CFG_FCS_INIT2F 15,  1
#define FIELD_SYS_CFG_PHR_MODE   16,  2
#define FIELD_SYS_CFG_DIS_STXP   18,  1
#define FIELD_SYS_CFG_RXM110K    22,  1
#define FIELD_SYS_CFG_RXWTOE     28,  1
#define FIELD_SYS_CFG_RXAUTR     29,  1
#define FIELD_SYS_CFG_AUTOACK    30,  1
#define FIELD_SYS_CFG_AACKPEND   31,  1

#define FIELD_TX_FCTRL_TFLEN      0,  7
#define FIELD_TX_FCTRL_TFLE       7,  3
#define FIELD_TX_FCTRL_R         10,  3
#define FIELD_TX_FCTRL_TXBR      13,  2
#define FIELD_TX_FCTRL_TR        15,  1
#define FIELD_TX_FCTRL_TXPRF     16,  2
#define FIELD_TX_FCTRL_TXPSR     18,  2
#define FIELD_TX_FCTRL_PE        20,  2
#define FIELD_TX_FCTRL_TXBOFFS   22, 10
#define FIELD_TX_FCTRL_IFSDELAY  32,  8

#define FIELD_SYS_CTRL_SFCST      0,  1
#define FIELD_SYS_CTRL_TXSTRT     1,  1
#define FIELD_SYS_CTRL_TXDLYS     2,  1
#define FIELD_SYS_CTRL_CANSFCS    3,  1
#define FIELD_SYS_CTRL_TRXOFF     6,  1
#define FIELD_SYS_CTRL_WAIT4RESP  7,  1
#define FIELD_SYS_CTRL_RXENAB     8,  1
#define FIELD_SYS_CTRL_RXDLYE     9,  1
#define FIELD_SYS_CTRL_HRBPT     24,  1

#define FIELD_SYS_MASK_MCPLOCK    1,  1
#define FIELD_SYS_MASK_MESYNCR    2,  1
#define FIELD_SYS_MASK_MAAT       3,  1
#define FIELD_SYS_MASK_MTXFRB     4,  1
#define FIELD_SYS_MASK_MTXPRS     5,  1
#define FIELD_SYS_MASK_MTXPHS     6,  1
#define FIELD_SYS_MASK_MTXFRS     7,  1
#define FIELD_SYS_MASK_MRXPRD     8,  1
#define FIELD_SYS_MASK_MRXSFDD    9,  1
#define FIELD_SYS_MASK_MLDEDONE  10,  1
#define FIELD_SYS_MASK_MRXPHD    11,  1
#define FIELD_SYS_MASK_MRXPHE    12,  1
#define FIELD_SYS_MASK_MRXDFR    13,  1
#define FIELD_SYS_MASK_MRXFCG    14,  1
#define FIELD_SYS_MASK_MRXFCE    15,  1
#define FIELD_SYS_MASK_MRXRFSL   16,  1
#define FIELD_SYS_MASK_MRXRFTO   17,  1
#define FIELD_SYS_MASK_MLDEERR   18,  1
#define FIELD_SYS_MASK_MRXOVRR   20,  1
#define FIELD_SYS_MASK_MRXPTO    21,  1
#define FIELD_SYS_MASK_MGPIORIQ  22,  1
#define FIELD_SYS_MASK_MSLP2INIT 23,  1
#define FIELD_SYS_MASK_MRFPLLLL  24,  1
#define FIELD_SYS_MASK_MCPLLLL   25,  1
#define FIELD_SYS_MASK_MRXSFDTO  26,  1
#define FIELD_SYS_MASK_MHPDWARN  27,  1
#define FIELD_SYS_MASK_MTXBERR   28,  1
#define FIELD_SYS_MASK_MAFFREJ   29,  1

#define FIELD_SYS_STATUS_IRQS      0,  1
#define FIELD_SYS_STATUS_CPLOCK    1,  1
#define FIELD_SYS_STATUS_ESYNCR    2,  1
#define FIELD_SYS_STATUS_AAT       3,  1
#define FIELD_SYS_STATUS_TXFRB     4,  1
#define FIELD_SYS_STATUS_TXPRS     5,  1
#define FIELD_SYS_STATUS_TXPHS     6,  1
#define FIELD_SYS_STATUS_TXFRS     7,  1
#define FIELD_SYS_STATUS_RXPRD     8,  1
#define FIELD_SYS_STATUS_RXSFDD    9,  1
#define FIELD_SYS_STATUS_LDEDONE  10,  1
#define FIELD_SYS_STATUS_RXPHD    11,  1
#define FIELD_SYS_STATUS_RXPHE    12,  1
#define FIELD_SYS_STATUS_RXDFR    13,  1
#define FIELD_SYS_STATUS_RXFCG    14,  1
#define FIELD_SYS_STATUS_RXFCE    15,  1
#define FIELD_SYS_STATUS_RXRFSL   16,  1
#define FIELD_SYS_STATUS_RXRFTO   17,  1
#define FIELD_SYS_STATUS_LDEERR   18,  1
#define FIELD_SYS_STATUS_RXOVRR   20,  1
#define FIELD_SYS_STATUS_RXPTO    21,  1
#define FIELD_SYS_STATUS_GPIORIQ  22,  1
#define FIELD_SYS_STATUS_SLP2INIT 23,  1
#define FIELD_SYS_STATUS_RFPLLLL  24,  1
#define FIELD_SYS_STATUS_CPLLLL   25,  1
#define FIELD_SYS_STATUS_RXSFDTO  26,  1
#define FIELD_SYS_STATUS_HPDWARN  27,  1
#define FIELD_SYS_STATUS_TXBERR   28,  1
#define FIELD_SYS_STATUS_AFFREJ   29,  1
#define FIELD_SYS_STATUS_HSRBP    30,  1
#define FIELD_SYS_STATUS_ICRBP    31,  1
#define FIELD_SYS_STATUS_RXRSCS   32,  1
#define FIELD_SYS_STATUS_RXPREJ   33,  1
#define FIELD_SYS_STATUS_TXPUTE   34,  1

#define FIELD_RX_FINFO_RXFLEN      0,  7
#define FIELD_RX_FINFO_RXFLE       7,  3
#define FIELD_RX_FINFO_RXNSPL     11,  2
#define FIELD_RX_FINFO_RXBR       13,  2
#define FIELD_RX_FINFO_RNG        15,  1
#define FIELD_RX_FINFO_RXPRF      16,  2
#define FIELD_RX_FINFO_RXPSR      18,  2
#define FIELD_RX_FINFO_RXPACC     20, 12

#define FIELD_RX_FQUAL_STD_NOISE   0, 16
#define FIELD_RX_FQUAL_FP_AMPL2   16, 16
#define FIELD_RX_FQUAL_FP_AMPL3   32, 16
#define FIELD_RX_FQUAL_CIR_PWR    48, 16

#define FIELD_RX_TTCKI_RXTTCKI     0, 32

#define FIELD_RX_TTCKO_RXTOFS      0, 19
#define FIELD_RX_TTCKO_RSMPDEL    24,  8
#define FIELD_RX_TTCKO_RCPHASE    32,  7

#define FIELD_RX_TIME_RX_STAMP     0, 40
#define FIELD_RX_TIME_FP_INDEX    40, 16
#define FIELD_RX_TIME_FP_AMPL1    56, 16
#define FIELD_RX_TIME_RX_RAWST    72, 40

#define FIELD_TX_TIME_TX_STAMP     0, 40
#define FIELD_TX_TIME_TX_RAWST    40, 40

#define FIELD_ACK_RESP_W4R_TIM     0, 20
#define FIELD_ACK_RESP_ACK_TIM    24,  8

#define FIELD_RX_SNIFF_SNIFF_ONT   0,  4
#define FIELD_RX_SNIFF_SNIFF_OFFT  8,  8

/* When DIS_STXP is 0 */
#define FIELD_TX_POWER_BOOSTNORM   0,  8
#define FIELD_TX_POWER_BOOSTP500   8,  8
#define FIELD_TX_POWER_BOOSTP250  16,  8
#define FIELD_TX_POWER_BOOSTP125  24,  8

/* When DIS_STXP is 1 */
#define FIELD_TX_POWER_TXPOWPHR    8,  8
#define FIELD_TX_POWER_TXPOWSD    16,  8

#define FIELD_CHAN_CTRL_TX_CHAN    0,  4
#define FIELD_CHAN_CTRL_RX_CHAN    4,  4
#define FIELD_CHAN_CTRL_DWSFD     17,  1
#define FIELD_CHAN_CTRL_RXPRF     18,  2
#define FIELD_CHAN_CTRL_TNSSFD    20,  1
#define FIELD_CHAN_CTRL_RNSSFD    21,  1
#define FIELD_CHAN_CTRL_TX_PCODE  22,  5
#define FIELD_CHAN_CTRL_RX_PCODE  27,  5

#define FIELD_AGC_CTRL1_DIS_AM     0,  1

#define FIELD_AGC_STAT1_EDG1       6,  5
#define FIELD_AGC_STAT1_EDV2      11,  9

#define FIELD_EC_CTRL_OSTSM        0,  1
#define FIELD_EC_CTRL_OSRSM        1,  1
#define FIELD_EC_CTRL_PLLLDT       2,  1
#define FIELD_EC_CTRL_WAIT         3,  8
#define FIELD_EC_CTRL_OSTRM       11,  1

#define FIELD_EC_RXTC_RX_TS_EST    0, 32

#define FIELD_EC_GOLP_OFFSET_EXT   0,  6

#define FIELD_GPIO_MODE_MSGP0      6,  2
#define FIELD_GPIO_MODE_MSGP1      8,  2
#define FIELD_GPIO_MODE_MSGP2     10,  2
#define FIELD_GPIO_MODE_MSGP3     12,  2
#define FIELD_GPIO_MODE_MSGP4     14,  2
#define FIELD_GPIO_MODE_MSGP5     16,  2
#define FIELD_GPIO_MODE_MSGP6     18,  2
#define FIELD_GPIO_MODE_MSGP7     20,  2
#define FIELD_GPIO_MODE_MSGP8     22,  2

#define FIELD_GPIO_DIR_GDP0        0,  1
#define FIELD_GPIO_DIR_GDP1        1,  1
#define FIELD_GPIO_DIR_GDP2        2,  1
#define FIELD_GPIO_DIR_GDP3        3,  1
#define FIELD_GPIO_DIR_GDM0        4,  1
#define FIELD_GPIO_DIR_GDM1        5,  1
#define FIELD_GPIO_DIR_GDM2        6,  1
#define FIELD_GPIO_DIR_GDM3        7,  1
#define FIELD_GPIO_DIR_GDP4        8,  1
#define FIELD_GPIO_DIR_GDP5        9,  1
#define FIELD_GPIO_DIR_GDP6       10,  1
#define FIELD_GPIO_DIR_GDP7       11,  1
#define FIELD_GPIO_DIR_GDM4       12,  1
#define FIELD_GPIO_DIR_GDM5       13,  1
#define FIELD_GPIO_DIR_GDM6       14,  1
#define FIELD_GPIO_DIR_GDM7       15,  1
#define FIELD_GPIO_DIR_GDP8       16,  1
#define FIELD_GPIO_DIR_GDM8       20,  1

#define FIELD_GPIO_DOUT_GOP0       0,  1
#define FIELD_GPIO_DOUT_GOP1       1,  1
#define FIELD_GPIO_DOUT_GOP2       2,  1
#define FIELD_GPIO_DOUT_GOP3       3,  1
#define FIELD_GPIO_DOUT_GOM0       4,  1
#define FIELD_GPIO_DOUT_GOM1       5,  1
#define FIELD_GPIO_DOUT_GOM2       6,  1
#define FIELD_GPIO_DOUT_GOM3       7,  1
#define FIELD_GPIO_DOUT_GOP4       8,  1
#define FIELD_GPIO_DOUT_GOP5       9,  1
#define FIELD_GPIO_DOUT_GOP6      10,  1
#define FIELD_GPIO_DOUT_GOP7      11,  1
#define FIELD_GPIO_DOUT_GOM4      12,  1
#define FIELD_GPIO_DOUT_GOM5      13,  1
#define FIELD_GPIO_DOUT_GOM6      14,  1
#define FIELD_GPIO_DOUT_GOM7      15,  1
#define FIELD_GPIO_DOUT_GOP8      16,  1
#define FIELD_GPIO_DOUT_GOM8      20,  1

#define FIELD_GPIO_IRQE_GIRQE0     0,  1
#define FIELD_GPIO_IRQE_GIRQE1     1,  1
#define FIELD_GPIO_IRQE_GIRQE2     2,  1
#define FIELD_GPIO_IRQE_GIRQE3     3,  1
#define FIELD_GPIO_IRQE_GIRQE4     4,  1
#define FIELD_GPIO_IRQE_GIRQE5     5,  1
#define FIELD_GPIO_IRQE_GIRQE6     6,  1
#define FIELD_GPIO_IRQE_GIRQE7     7,  1
#define FIELD_GPIO_IRQE_GIRQE8     8,  1

#define FIELD_GPIO_ISEN_GISEN0     0,  1
#define FIELD_GPIO_ISEN_GISEN1     1,  1
#define FIELD_GPIO_ISEN_GISEN2     2,  1
#define FIELD_GPIO_ISEN_GISEN3     3,  1
#define FIELD_GPIO_ISEN_GISEN4     4,  1
#define FIELD_GPIO_ISEN_GISEN5     5,  1
#define FIELD_GPIO_ISEN_GISEN6     6,  1
#define FIELD_GPIO_ISEN_GISEN7     7,  1
#define FIELD_GPIO_ISEN_GISEN8     8,  1

#define FIELD_GPIO_IMODE_GIMOD0    0,  1
#define FIELD_GPIO_IMODE_GIMOD1    1,  1
#define FIELD_GPIO_IMODE_GIMOD2    2,  1
#define FIELD_GPIO_IMODE_GIMOD3    3,  1
#define FIELD_GPIO_IMODE_GIMOD4    4,  1
#define FIELD_GPIO_IMODE_GIMOD5    5,  1
#define FIELD_GPIO_IMODE_GIMOD6    6,  1
#define FIELD_GPIO_IMODE_GIMOD7    7,  1
#define FIELD_GPIO_IMODE_GIMOD8    8,  1

#define FIELD_GPIO_IBES_GIBES0     0,  1
#define FIELD_GPIO_IBES_GIBES1     1,  1
#define FIELD_GPIO_IBES_GIBES2     2,  1
#define FIELD_GPIO_IBES_GIBES3     3,  1
#define FIELD_GPIO_IBES_GIBES4     4,  1
#define FIELD_GPIO_IBES_GIBES5     5,  1
#define FIELD_GPIO_IBES_GIBES6     6,  1
#define FIELD_GPIO_IBES_GIBES7     7,  1
#define FIELD_GPIO_IBES_GIBES8     8,  1

#define FIELD_GPIO_ICLR_GICLR0     0,  1
#define FIELD_GPIO_ICLR_GICLR1     1,  1
#define FIELD_GPIO_ICLR_GICLR2     2,  1
#define FIELD_GPIO_ICLR_GICLR3     3,  1
#define FIELD_GPIO_ICLR_GICLR4     4,  1
#define FIELD_GPIO_ICLR_GICLR5     5,  1
#define FIELD_GPIO_ICLR_GICLR6     6,  1
#define FIELD_GPIO_ICLR_GICLR7     7,  1
#define FIELD_GPIO_ICLR_GICLR8     8,  1

#define FIELD_GPIO_IDBE_GIDBE0     0,  1
#define FIELD_GPIO_IDBE_GIDBE1     1,  1
#define FIELD_GPIO_IDBE_GIDBE2     2,  1
#define FIELD_GPIO_IDBE_GIDBE3     3,  1
#define FIELD_GPIO_IDBE_GIDBE4     4,  1
#define FIELD_GPIO_IDBE_GIDBE5     5,  1
#define FIELD_GPIO_IDBE_GIDBE6     6,  1
#define FIELD_GPIO_IDBE_GIDBE7     7,  1
#define FIELD_GPIO_IDBE_GIDBE8     8,  1

#define FIELD_GPIO_RAW_GRAWP0      0,  1
#define FIELD_GPIO_RAW_GRAWP1      1,  1
#define FIELD_GPIO_RAW_GRAWP2      2,  1
#define FIELD_GPIO_RAW_GRAWP3      3,  1
#define FIELD_GPIO_RAW_GRAWP4      4,  1
#define FIELD_GPIO_RAW_GRAWP5      5,  1
#define FIELD_GPIO_RAW_GRAWP6      6,  1
#define FIELD_GPIO_RAW_GRAWP7      7,  1
#define FIELD_GPIO_RAW_GRAWP8      8,  1

#define FIELD_RF_CONF_TXFEN        8,  5
#define FIELD_RF_CONF_PLLFEN      13,  3
#define FIELD_RF_CONF_LDOFEN      16,  5
#define FIELD_RF_CONF_TXRXSW      21,  2

#define FIELD_RX_TXCTRL_TXMTUNE    5,  4
#define FIELD_RX_TXCTRL_TXMQ       9,  3

#define FIELD_RF_STATUS_CPLLLOCK   0,  1
#define FIELD_RF_STATUS_CPLLLOW    1,  1
#define FIELD_RF_STATUS_CPLLHIGH   2,  1
#define FIELD_RF_STATUS_RFPLLLOCK  3,  1

#define FIELD_LDOTUNE_LDOTUNE      0, 40

#define FIELD_TC_SARC_SAR_CTRL     0,  1

#define FIELD_TC_SARL_SAR_LVBAT    0,  8
#define FIELD_TC_SARL_SAR_LTEMP    8,  8

#define FIELD_TC_SARW_SAR_WVBAT    0,  8
#define FIELD_TC_SARW_SAR_WTEMP    8,  8

#define FIELD_FS_XTALT_XTALT       0,  5
#define FIELD_FS_XTALT_RESERVED    5,  3

#define FIELD_AON_WCFG_ONW_RADC    0,  1
#define FIELD_AON_WCFG_ONW_RX      1,  1
#define FIELD_AON_WCFG_ONW_LEUI    3,  1
#define FIELD_AON_WCFG_ONW_LDC     6,  1
#define FIELD_AON_WCFG_ONW_L64P    7,  1
#define FIELD_AON_WCFG_PRES_SLEEP  8,  1
#define FIELD_AON_WCFG_ONW_LLDE   11,  1
#define FIELD_AON_WCFG_ONW_LLDO   12,  1

#define FIELD_AON_CTRL_RESTORE     0,  1
#define FIELD_AON_CTRL_SAVE        1,  1
#define FIELD_AON_CTRL_UPL_CFG     2,  1
#define FIELD_AON_CTRL_DCA_READ    3,  1
#define FIELD_AON_CTRL_DCA_ENAB    7,  1

#define FIELD_AON_CFG0_SLEEP_EN    0,  1
#define FIELD_AON_CFG0_WAKE_PIN    1,  1
#define FIELD_AON_CFG0_WAKE_SPI    2,  1
#define FIELD_AON_CFG0_WAKE_CNT    3,  1
#define FIELD_AON_CFG0_LPDIV_EN    4,  1
#define FIELD_AON_CFG0_LPCLKDIVA   5, 11
#define FIELD_AON_CFG0_SLEEP_TIM  16, 16

#define FIELD_AON_CFG1_SLEEP_CE    0,  1
#define FIELD_AON_CFG1_SMXX        1,  1
#define FIELD_AON_CFG1_LPOSC_C     2,  1

#define FIELD_OTP_ADDR_OTPADDR     0, 11

#define FIELD_OTP_CTRL_OTPRDEN     0,  1
#define FIELD_OTP_CTRL_OTPREAD     1,  1
#define FIELD_OTP_CTRL_OTPMRWR     3,  1
#define FIELD_OTP_CTRL_OTPPROG     6,  1
#define FIELD_OTP_CTRL_OTPMR       7,  4
#define FIELD_OTP_CTRL_LDELOAD    15,  1

#define FIELD_OTP_STAT_OTPPRGD     0,  1
#define FIELD_OTP_STAT_OTPPVOK     1,  1

#define FIELD_OTP_SF_OPS_KICK      0,  1
#define FIELD_OTP_SF_LDO_KICK      1,  1
#define FIELD_OTP_SF_OPS_OPS_SEL   4,  1

#define FIELD_LDE_CFG1_NTM         0,  5
#define FIELD_LDE_CFG1_PMULT       5,  3

#define FIELD_EVC_CTRL_EVC_EN      0,  1
#define FIELD_EVC_CTRL_EVC_CLR     1,  1

#define FIELD_EVC_PHE_EVC_PHE      0, 12
#define FIELD_EVC_RSE_EVC_RSE      0, 12
#define FIELD_EVC_FCG_EVC_FCG      0, 12
#define FIELD_EVC_FCE_EVC_FCE      0, 12
#define FIELD_EVC_FFR_EVC_FFR      0, 12
#define FIELD_EVC_OVR_EVC_OVR      0, 12
#define FIELD_EVC_STO_EVC_STO      0, 12
#define FIELD_EVC_PTO_EVC_PTO      0, 12
#define FIELD_EVC_FWTO_EVC_FWTO    0, 12
#define FIELD_EVC_TXFS_EVC_TXFS    0, 12
#define FIELD_EVC_HPW_EVC_HPW      0, 12
#define FIELD_EVC_TPW_EVC_TPW      0, 12

#define FIELD_DIAG_TMC_TX_PSTM     4,  1

#define FIELD_PMSC_CTRL0_SYSCLKS    0,  2
#define FIELD_PMSC_CTRL0_RXCLKS     2,  2
#define FIELD_PMSC_CTRL0_TXCLKS     4,  2
#define FIELD_PMSC_CTRL0_FACE       6,  1
/* OTP and LDE are undocumented */
#define FIELD_PMSC_CTRL0_LDE        8,  1
#define FIELD_PMSC_CTRL0_OTP        9,  1
#define FIELD_PMSC_CTRL0_ADCCE     10,  1
#define FIELD_PMSC_CTRL0_AMCE      15,  1
#define FIELD_PMSC_CTRL0_GPCE      16,  1
#define FIELD_PMSC_CTRL0_GPRN      17,  1
#define FIELD_PMSC_CTRL0_GPDCE     18,  1
#define FIELD_PMSC_CTRL0_GPDRN     19,  1
#define FIELD_PMSC_CTRL0_KHZCLKEN  23,  1
#define FIELD_PMSC_CTRL0_SOFTRESET 28,  4

#define FIELD_PMSC_CTRL1_ARX2INIT   1,  1
#define FIELD_PMSC_CTRL1_PKTSEQ     3,  8
#define FIELD_PMSC_CTRL1_ATXSLP    11,  1
#define FIELD_PMSC_CTRL1_ARXSLP    12,  1
#define FIELD_PMSC_CTRL1_SNOZE     13,  1
#define FIELD_PMSC_CTRL1_SNOZR     14,  1
#define FIELD_PMSC_CTRL1_PLLSYN    15,  1
#define FIELD_PMSC_CTRL1_LDERUNE   17,  1
#define FIELD_PMSC_CTRL1_KHZCLKDIV 26,  6

#define FIELD_PMSC_SNOZT_SNOZ_TIM   0,  8

#define FIELD_PMSC_TXFSEQ_TXFINESEQ 0, 16

#define FIELD_PMSC_LEDC_BLINK_TIM   0,  8
#define FIELD_PMSC_LEDC_BLNKEN      8,  1
#define FIELD_PMSC_LEDC_BLNKNOW    16,  4


#define OTP_EUID_LOW                0x000
#define OTP_EUID_HIGH               0x001
#define OTP_AEUID_LOW               0x002
#define OTP_AEUID_HIGH              0x003
#define OTP_LDOTUNE_CAL_LOW         0x004
#define OTP_LDOTUNE_CAL_HIGH        0x005
#define OTP_CHIP_ID                 0x006
#define OTP_LOT_ID                  0x007
#define OTP_VOLTAGE_CAL             0x008
#define OTP_TEMPERATURE_CAL         0x009
#define OTP_RESERVED_00A            0x00A
#define OTP_RESERVED_00B            0x00B
#define OTP_RESERVED_00C            0x00C
#define OTP_RESERVED_00D            0x00D
#define OTP_RESERVED_00E            0x00E
#define OTP_RESERVED_00F            0x00F
#define OTP_CH1_TX_POWER_PRF16      0x010
#define OTP_CH1_TX_POWER_PRF64      0x011
#define OTP_CH2_TX_POWER_PRF16      0x012
#define OTP_CH2_TX_POWER_PRF64      0x013
#define OTP_CH3_TX_POWER_PRF16      0x014
#define OTP_CH3_TX_POWER_PRF64      0x015
#define OTP_CH4_TX_POWER_PRF16      0x016
#define OTP_CH4_TX_POWER_PRF64      0x017
#define OTP_CH5_TX_POWER_PRF16      0x018
#define OTP_CH5_TX_POWER_PRF64      0x019
#define OTP_CH7_TX_POWER_PRF16      0x01A
#define OTP_CH7_TX_POWER_PRF64      0x01B
#define OTP_ANETNNA_DELAY           0x01C
#define OTP_RESERVED_01D            0x01D
#define OTP_XTAL_TRIM               0x01E
#define OTP_RESERVED_01F            0x01F

#define OTP_SR                      0x400

#endif /* _RADIO_REG_H */
