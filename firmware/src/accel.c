/* accel.c */

#include "accel.h"
#include "accel_spi.h"
#include <stdbool.h>

void accel_init(void)
{
    volatile int count;
    accel_spi_init();

    accel_write(0x10, 0x01);
    accel_write(0x24, 0x40);

    for (count = 0; count < 100000; count++) ;

    accel_write(0x0d, 0x80);
    accel_write(0x20, 0x01);
    accel_write(0x21, 0x80);
    accel_write(0x28, 0x00);
    accel_write(0x1A, 0x00);
}

uint8_t accel_read(uint8_t addr)
{
    uint8_t data;

    addr = addr | 0xc0;

    accel_spi_start();
    accel_spi_write(addr);

    data = accel_spi_read();
    accel_spi_stop();

    return data;
}

void accel_write(uint8_t addr, uint8_t data)
{
    accel_spi_start();

    addr = addr | 0x40;

    accel_spi_write(addr);
    accel_spi_write(data);

    accel_spi_stop();
}
