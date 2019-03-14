/* battery.c */

#include "em_gpio.h"

/* BAT_MON is PD6
 * BAT_MON_EN is PD7
 */

#include "battery.h"
#include "adc.h"

void battery_init(void)
{
    GPIO_PinModeSet(gpioPortD, 7, gpioModePushPull, 0);

    adc_init();
}

uint16_t battery_read(void)
{
    uint16_t reading;

    GPIO_PinModeSet(gpioPortD, 7, gpioModePushPull, 1);

    reading = adc_read();

    GPIO_PinModeSet(gpioPortD, 7, gpioModePushPull, 0);

    return reading;
}

/* mV */
#define FULL_SCALE 5000
#define FULL  READING_FOR_MV(4100)
#define MIN   READING_FOR_MV(2000)
#define EMPTY READING_FOR_MV(3600)

#define READING_FOR_MV(x) ((32768 * (x)) / FULL_SCALE)

uint8_t battery_state(uint16_t voltage)
{
    if (voltage > FULL)
        return 254;
    if (voltage < MIN)
        return 0; /* No information */
    if (voltage < EMPTY)
        return 1;
    /* For now, let's use a linear estimator. This needs to be
     * updated after discharge curve measurements.
     */
    return ((253 * (voltage - EMPTY)) / (FULL - EMPTY)) + 1;
}
