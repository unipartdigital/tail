/* battery.h */

#ifndef _BATTERY_H
#define _BATTERY_H

#include <stdint.h>

void battery_init(void);
uint16_t battery_read(void);
uint8_t battery_state(uint16_t voltage);

#endif /* _BATTERY_H */
