/* accel_spi.h */

#ifndef _ACCEL_SPI_H
#define _ACCEL_SPI_H

#include <stdint.h>

void accel_spi_init(void);
void accel_spi_start(void);
void accel_spi_stop(void);
void accel_spi_write(uint8_t value);
uint8_t accel_spi_read(void);
void accel_spi_wakeup(void);

#endif /* _ACCEL_SPI_H */
