/* radio_spi.h */

#ifndef _RADIO_SPI_H
#define _RADIO_SPI_H

#include <stdint.h>
#include <stdbool.h>

void radio_spi_init(void);
void radio_spi_start(void);
void radio_spi_stop(void);
void radio_spi_write(uint8_t value);
uint8_t radio_spi_read(void);
void radio_spi_wakeup(void);
void radio_spi_speed(bool fast);

#endif /* _RADIO_SPI_H */
