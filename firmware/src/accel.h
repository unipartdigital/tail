/* accel.h */

#ifndef _ACCEL_H
#define _ACCEL_H

#include <stdint.h>
#include <stdbool.h>

bool accel_init(void);
uint8_t accel_read(uint8_t addr);
void accel_write(uint8_t addr, uint8_t data);

void accel_config_interrupts(void);
void accel_config_power_mode(int wake_mode, int sniff_mode);
void accel_config_rate(int rate);
void accel_config_range_resolution(int range, int res);
void accel_config_sniff_rate(int sniff_rate, int standby_rate);
void accel_config_threshold(int x, int y, int z, int shift);
void accel_config_detection_count(int x, int y, int z, int enable);
void accel_config_sniff_mode(bool and, bool c2b);
void accel_enter_mode(int mode);
void accel_enable_axis(bool x, bool y, bool z);
void accel_readings(uint16_t *x, uint16_t *y, uint16_t *z);
void accel_test(int x, int y, int z);
bool accel_interrupt_fired(void);
uint32_t accel_last_activity(void);

/* Modes */

#define ACCEL_SLEEP     0x00
#define ACCEL_STANDBY   0x01
#define ACCEL_SNIFF     0x02
#define ACCEL_CWAKE     0x05
#define ACCEL_SWAKE     0x06
#define ACCEL_TRIG      0x07

/* Power modes */
#define ACCEL_LP   0
#define ACCEL_ULP  3
#define ACCEL_PM   4

/* Range and resolution */

#define ACCEL_6BITS   0
#define ACCEL_7BITS   1
#define ACCEL_8BITS   2
#define ACCEL_10BITS  3
#define ACCEL_12BITS  4
#define ACCEL_14BITS  5

#define ACCEL_2G      0
#define ACCEL_4G      1
#define ACCEL_8G      2
#define ACCEL_16G     3
#define ACCEL_12G     4

/* Sniff rate */

#define ACCEL_ULP_SR_DEFAULT  0
#define ACCEL_ULP_SR_0P4      1
#define ACCEL_ULP_SR_0P8      2
#define ACCEL_ULP_SR_1P5      3
#define ACCEL_ULP_SR_6        4
#define ACCEL_ULP_SR_13       5
#define ACCEL_ULP_SR_25       6
#define ACCEL_ULP_SR_50       7
#define ACCEL_ULP_SR_100      8
#define ACCEL_ULP_SR_190      9
#define ACCEL_ULP_SR_380     10
#define ACCEL_ULP_SR_750     11
#define ACCEL_ULP_SR_1100    12
#define ACCEL_ULP_SR_1300    15

#define ACCEL_LP_SR_DEFAULT   0
#define ACCEL_LP_SR_0P4       1
#define ACCEL_LP_SR_0P8       2
#define ACCEL_LP_SR_1P5       3
#define ACCEL_LP_SR_7         4
#define ACCEL_LP_SR_14        5
#define ACCEL_LP_SR_28        6
#define ACCEL_LP_SR_54        7
#define ACCEL_LP_SR_105       8
#define ACCEL_LP_SR_210       9
#define ACCEL_LP_SR_400      10
#define ACCEL_LP_SR_600      11
#define ACCEL_LP_SR_750      15

#define ACCEL_PM_SR_DEFAULT   0
#define ACCEL_PM_SR_0P2       1
#define ACCEL_PM_SR_0P4       2
#define ACCEL_PM_SR_0P9       3
#define ACCEL_PM_SR_7         4
#define ACCEL_PM_SR_14        5
#define ACCEL_PM_SR_28        6
#define ACCEL_PM_SR_55        7
#define ACCEL_PM_SR_80        8
#define ACCEL_PM_SR_100      15

/* Standby rate */

#define ACCEL_ULP_STB_1       0
#define ACCEL_ULP_STB_3       1
#define ACCEL_ULP_STB_5       2
#define ACCEL_ULP_STB_10      3
#define ACCEL_ULP_STB_23      4
#define ACCEL_ULP_STB_45      5
#define ACCEL_ULP_STB_90      6
#define ACCEL_ULP_STB_180     7

#define ACCEL_LP_STB_0P5      0
#define ACCEL_LP_STB_1        1
#define ACCEL_LP_STB_3        2
#define ACCEL_LP_STB_6        3
#define ACCEL_LP_STB_12       4
#define ACCEL_LP_STB_24       5
#define ACCEL_LP_STB_48       6
#define ACCEL_LP_STB_100      7

#define ACCEL_PM_STB_0P1      0
#define ACCEL_PM_STB_0P2      1
#define ACCEL_PM_STB_0P4      2
#define ACCEL_PM_STB_0P8      3
#define ACCEL_PM_STB_1P5      4
#define ACCEL_PM_STB_3        5
#define ACCEL_PM_STB_5        6
#define ACCEL_PM_STB_10       7

/* CWAKE rate */

#define ACCEL_ULP_ODR_25      6
#define ACCEL_ULP_ODR_50      7
#define ACCEL_ULP_ODR_100     8
#define ACCEL_ULP_ODR_190     9
#define ACCEL_ULP_ODR_380    10
#define ACCEL_ULP_ODR_750    11
#define ACCEL_ULP_ODR_1100   12
#define ACCEL_ULP_ODR_1300   15

#define ACCEL_LP_ODR_14      5
#define ACCEL_LP_ODR_28      6
#define ACCEL_LP_ODR_54      7
#define ACCEL_LP_ODR_105     8
#define ACCEL_LP_ODR_210     9
#define ACCEL_LP_ODR_400    10
#define ACCEL_LP_ODR_600    11
#define ACCEL_LP_ODR_750    15

#define ACCEL_PM_ODR_14      5
#define ACCEL_PM_ODR_25      6
#define ACCEL_PM_ODR_55      7
#define ACCEL_PM_ODR_80      8
#define ACCEL_PM_ODR_100    15

#endif /* _ACCEL_H */
