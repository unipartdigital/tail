/* accel_reg.h */

#ifndef _ACCEL_REG_H
#define _ACCEL_REG_H

#define EXT_STAT_1 0x00
#define EXT_STAT_2 0x01
#define XOUT_LSB   0x02
#define XOUT_MSB   0x03
#define YOUT_LSB   0x04
#define YOUT_MSB   0x05
#define ZOUT_LSB   0x06
#define ZOUT_MSB   0x07
#define STATUS_1   0x08
#define STATUS_2   0x09

#define FREG_1     0x0D
#define FREG_2     0x0E
#define INIT_1     0x0F
#define MODE_C     0x10
#define RATE_1     0x11
#define SNIFF_C    0x12
#define SNIFFTH_C  0x13
#define SNIFFCF_C  0x14
#define RANGE_C    0x15
#define FIFO_C     0x16
#define INTR_C     0x17

#define INIT_3     0x1A
#define SCRATCH    0x1B
#define PMCR       0x1C

#define DMX        0x20
#define DMY        0x21
#define DMZ        0x22

/* Note that this register name conflicts with a field name */
#define RESET_C    0x24

#define INIT_2     0x28
#define TRIGC      0x29
#define XOFFL      0x2A
#define XOFFH      0x2B
#define YOFFL      0x2C
#define YOFFH      0x2D
#define ZOFFL      0x2E
#define ZOFFH      0x2F
#define XGAIN      0x30
#define YGAIN      0x31
#define ZGAIN      0x32

/* EXT_STAT1 */
#define I2C_AD0      0x08

/* EXT_STAT2 */
#define SNIFF_DETECT 0x80
#define SNIFF_EN     0x40
#define OTP_BUSY     0x20
#define PD_CLK_STAT  0x02
#define OVR_DATA     0x01

/* STATUS_1 */
#define INT_PEND     0x80
#define FIFO_TRHESH  0x40
#define FIFO_FULL    0x20
#define FIFO_EMPTY   0x10
#define NEW_DATA     0x08
#define MODE         0x07

/* STATUS_2 */
#define INT_SWAKE       0x80
#define INT_FIFO_TRHESH 0x40
#define INT_FIFO_FULL   0x20
#define INT_FIFO_EMPTY  0x10
#define INT_ACQ         0x08
#define INT_WAKE        0x04

/* FREG_1 */
#define SPI_EN          0x80
#define I2C_EN          0x40
#define SPI3_EN         0x20
#define INTSC_EN        0x10
#define FREEZE          0x08

/* FREG_2 */
#define EXT_TRIG_EN     0x80
#define EXT_TRIG_POL    0x40
#define FIFO_STREAM     0x20
#define I2CINIT_WRCLRE  0x10
#define FIFO_STAT_EN    0x08
#define SPI_STAT_EN     0x04
#define FIFO_BURST      0x02
#define WRAPA           0x01

/* INIT_1 */
#define WAKING_UP       0x40
#define INIT_VALUE      0x42
#define DEVICE_READY    0x43

/* MODE_C */
#define TRIG_CMD        0x80
#define Z_AXIS_PD       0x40
#define Y_AXIS_PD       0x20
#define X_AXIS_PD       0x10
#define MCTRL(x)        ((x) << 0)

#define SLEEP           0x00
#define STANDBY         0x01
#define SNIFF           0x02
#define CWAKE           0x05
#define SWAKE           0x06
#define TRIG            0x07

/* SNIFF_C */
#define STB_RATE(x)     ((x) << 5)
#define SNIFF_SR(x)     ((x) << 0)

/* SNIFFTH_C */
#define SNIFF_MODE      0x80
#define SNIFF_AND_OR    0x40
#define SNIFF_TH(x)     ((x) << 0)

/* SNIFFCF_C */
#define SNIFF_RESET     0x80
#define SNIFF_MUX(x)    ((x) << 4)
#define SNIFF_CNTEN     0x08
#define SNIFF_THADR(x)  ((x) << 0)

#define SNIFF_TH_X      0x01
#define SNIFF_TH_Y      0x02
#define SNIFF_TH_Z      0x03

#define SNIFF_X_COUNT   0x05
#define SNIFF_Y_COUNT   0x06
#define SNIFF_Z_COUNT   0x07

/* RANGE_C */
#define RANGE(x)        ((x) << 4)
#define RES(x)          ((x) << 0)

/* FIFO_C */
#define FIFO_RESET      0x80
#define FIFO_EN         0x40
#define FIFO_MODE       0x20
#define FIFO_TH(x)      ((x) << 0)

/* INTR_C */
#define INT_SWAKE       0x80
#define INT_FIFO_TRHESH 0x40
#define INT_FIFO_FULL   0x20
#define INT_FIFO_EMPTY  0x10
#define INT_ACQ         0x08
#define INT_WAKE        0x04
#define IAH             0x02
#define IPP             0x01

/* PMCR */
#define SPM(x)          ((x) << 4)
#define CSPM(x)         ((x) << 0)

/* DMX */
#define DMX_INIT        0x01
#define DNX             0x08
#define DPX             0x04

/* DMY */
#define DMY_INIT        0x80
#define DNY             0x08
#define DPY             0x04

/* DMZ */
#define DMZ_INIT        0x00
#define DNZ             0x08
#define DPZ             0x04

/* RESET */
#define RELOAD          0x80
#define RESET           0x40



#endif /* _ACCEL_REG_H */
