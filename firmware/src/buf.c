/* buf.c */

#include "buf.h"

void buf_init(buffer *b, uint8_t *data, int size)
{
	b->data = data;
	b->size = size;
	b->read = 0;
	b->write = 0;
}

/* Providing the compiler refrains from placing the final write to b->write
 * prior to the actual writing of the data in buf_put, and the final write
 * to b->read prior to the reading of the data in buf_get, it should be safe
 * to use an arrangement where one function is called only from interrupt
 * context and the other is never called from interrupt context, providing
 * that neither function is re-entered.
 */
bool buf_put(buffer *b, uint8_t item)
{
	int write = b->write;
	int read = b->read;
	int next = (write+1) % b->size;

	if (next == read)
		return false;

	b->data[write] = item;
	b->write = next;

	return true;
}

bool buf_get(buffer *b, uint8_t *item)
{
	int write = b->write;
	int read = b->read;

	if (write == read)
		return false;

	*item = b->data[read];
	b->read = (read+1) % b->size;

	return true;
}
