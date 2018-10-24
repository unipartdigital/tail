/* proto.h */

#ifndef _PROTO_H
#define _PROTO_H

#include <stdint.h>

#define ADDR_NONE 0
#define ADDR_SHORT 2
#define ADDR_LONG 3

#define PAN_UNASSOCIATED 0xffff
#define PAN_BROADCAST 0xffff

/* Time that we need in order to prepare for an event.
 * Estimate this based on the radio wakeup time with a safety
 * margin. Depending on the clock resolution there may be
 * rounding errors.
 */
#define PROTO_PREPARETIME TIME_FROM_MS(10)

typedef struct {
	int type;
	uint16_t pan;
	union {
		uint16_t s;
		uint64_t l;
	} a;
} address_t;

typedef uint8_t ipv6_addr_t[16];


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
void proto_turnaround_delay(uint32_t us);
void proto_rx_timeout(uint32_t time);
void tag_start(void);
void tag_with_period(int period);
void tag(void);
void tag_average(int period, int count);
void tagipv6_with_period(int period, int period_idle, int transition_time);
void tagipv6(void);
void anchor(void);
void stop(void);
void proto_poll();
void set_antenna_delay_tx(uint16_t delay);
void set_antenna_delay_rx(uint16_t delay);
void range_with_period(address_t *address, int period);
void range(address_t *address);
void range_average(address_t *address, int period, int count);
void ranchor(void);
int proto_volts(void);
int proto_temp(void);
void proto_prepare_immediate(void);

#endif
