/* proto.h */

#ifndef _PROTO_H
#define _PROTO_H

#include <stdint.h>

#define ADDR_NONE 0
#define ADDR_SHORT 2
#define ADDR_LONG 3

#define PAN_UNASSOCIATED 0xffff
#define PAN_BROADCAST 0xffff

#define ADDR_SHORT_BROADCAST 0xffff

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
void start_rx(bool delayed);
void proto_turnaround_delay(uint32_t us);
void proto_rx_timeout(uint32_t time);
void proto_rx_delay(uint32_t time);
void tag_with_period(int period, int period_idle, int transition_time);
void tag(void);
void stop(void);
void proto_poll();
void set_antenna_delay_tx(uint16_t delay);
void set_antenna_delay_rx(uint16_t delay);
int proto_volts(void);
int proto_temp(void);
int proto_rawvolts(void);
int proto_rawtemp(void);
uint32_t proto_uptime_blinks(void);
void proto_prepare_immediate(void);
uint16_t proto_battery_volts(void);

#endif
