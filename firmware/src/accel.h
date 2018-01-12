/* accel.h */

#ifndef _ACCEL_H
#define _ACCEL_H

#include <stdint.h>

void accel_init(void);
uint8_t accel_read(uint8_t addr);
void accel_write(uint8_t addr, uint8_t data);

#endif /* _ACCEL_H */
