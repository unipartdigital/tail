/* battery.c */

#include "em_gpio.h"

/* BAT_MON is PD6
 * BAT_MON_EN is PD7
 */

#include "battery.h"
#include "adc.h"

static bool battery_allow_flat;

void battery_init(bool allow_flat)
{
    GPIO_PinModeSet(gpioPortD, 7, gpioModePushPull, 0);

    adc_init();

    battery_allow_flat = allow_flat;
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
#define FULL  READING_FOR_MV(4150)
#define MIN   READING_FOR_MV(2000)
#define EMPTY READING_FOR_MV(3600)

#define READING_FOR_MV(x) ((32768 * (x)) / FULL_SCALE)

/* Returns 0-255 for battery state, or -1 if no info */
int battery_state(uint16_t voltage)
{
    if (voltage > FULL)
        return 255;
    if (voltage < MIN)
        return -1; /* No information */
    if (voltage < EMPTY)
        return 0;
    /* For now, let's use a linear estimator. This needs to be
     * updated after discharge curve measurements.
     */
    return ((255 * (voltage - EMPTY)) / (FULL - EMPTY));
}

bool battery_flat(uint16_t voltage)
{
	if (battery_allow_flat)
		return false;
	else
		return (voltage < EMPTY);
}
