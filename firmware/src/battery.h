/* battery.h */

#ifndef _BATTERY_H
#define _BATTERY_H

#include <stdint.h>

void battery_init(void);
uint16_t battery_read(void);
int battery_state(uint16_t voltage);
bool battery_flat(uint16_t voltage);

#endif /* _BATTERY_H */
