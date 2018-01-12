/* buf.h */

#ifndef _BUF_H
#define _BUF_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
	uint8_t *data;
	int size;
	volatile int read;
	volatile int write;
} buffer;

void buf_init(buffer *b, uint8_t *data, int size);
bool buf_put(buffer *b, uint8_t item);
bool buf_get(buffer *b, uint8_t *item);

#endif
