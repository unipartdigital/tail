/* proto.h */

#ifndef _PROTO_H
#define _PROTO_H

#include <stdint.h>

#define ADDR_NONE 0
#define ADDR_SHORT 2
#define ADDR_LONG 3

#define PAN_UNASSOCIATED 0
#define PAN_BROADCAST 0xffff

typedef struct {
	int type;
	uint16_t pan;
	union {
		uint16_t s;
		uint64_t l;
	} a;
} address_t;

void proto_init(void);
void start_rx(void);
void txdone(void);
void rxdone_anchor(void);
void txdone_tag(void);
void rxdone_tag(void);
void rxtimeout_tag(void);
void rxerror_tag(void);
void rxtimeout(void);
void rxerror(void);
void tag_start(void);
void tag_with_period(int period);
void tag(void);
void tag_average(int period, int count);
void anchor(void);
void stop(void);
void proto_poll();
void set_antenna_delay_tx(uint16_t delay);
void set_antenna_delay_rx(uint16_t delay);
void range_with_period(address_t *address, int period);
void range(address_t *address);
void range_average(address_t *address, int period, int count);
void ranchor(void);

#endif