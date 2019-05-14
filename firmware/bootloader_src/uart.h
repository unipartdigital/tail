/* uart.h */

#ifndef _UART_H
#define _UART_H

#include <stdbool.h>
#include <stdint.h>

void write_string(const char *s);
void write_int(uint32_t n);
void write_int64(uint64_t n);
void write_hex(uint32_t n);
void uart_init(void);
bool uart_tx(uint8_t data);
bool uart_rx(uint8_t *data);
bool uart_prepare_sleep(void);

#endif
