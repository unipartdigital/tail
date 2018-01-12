/* proto.c */

#include "radio.h"
#include "uart.h"
#include "time.h"
#include "proto.h"

#include "em_gpio.h"

#define BUFLEN 1024
#define HEADER_MAX 37

struct {
	volatile bool in_rxdone;
	volatile bool in_txdone;
	volatile bool in_rxtimeout;
	volatile bool in_rxerror;
	volatile bool in_despatch;
} debug;
uint8_t rxbuf[BUFLEN];
uint8_t txbuf[BUFLEN];

int tag_period;
bool tag_average_running;
bool tag_average_done;
int tag_count;
int tag_count_initial;
uint64_t td_sum;

int64_t transmit_time;
int64_t half_ping;
int64_t half_ping_distance;
volatile bool distance_valid;
volatile bool tag_packet_timeout;
volatile bool tag_packet_failed;

typedef struct {
	uint64_t tx_stamp;
	uint32_t rt1, rt2, tt1, tt2;
	uint32_t time;
	volatile uint32_t distance;
	volatile bool valid;
	int period;
	bool active;
	volatile bool timeout;
	volatile bool failed;
    address_t target_addr;
#if 1
	bool done;
	int count;
	int count_initial;
	int64_t sum;
	bool running;
#endif
} ranging_data_t;

ranging_data_t ranging;

typedef struct {
	uint64_t eui;
	uint16_t short_addr;
	uint16_t pan;
	bool associated;
	uint8_t seq;
	uint16_t antenna_delay_tx;
	uint16_t antenna_delay_rx;
	uint64_t *txtime_ptr;
	bool continuous_receive;
	bool receive_after_transmit;
} device_t;

device_t device = {
		.eui = 0,
		.short_addr = 0,
		.pan = 0,
		.associated = false,
		.seq = 0,
		.antenna_delay_tx = 0,
		.antenna_delay_rx = 0,
		.txtime_ptr = NULL,
		.continuous_receive = false,
		.receive_after_transmit = false
};

#define READ16(buf, i) (buf[i] + (buf[i+1] << 8))
#define READ32(buf, i) (READ16(buf, i) + (((uint32_t)READ16(buf, i+2)) << 16))
#define READ64(buf, i) (READ32(buf, i) + (((uint64_t)READ32(buf, i+4)) << 32))

#define WRITE16(buf, i, v) do { \
        buf[i] =   ((v >> 0) & 0xff); \
        buf[i+1] = ((v >> 8) & 0xff); \
} while (0)
#define WRITE32(buf, i, v) do { \
        buf[i] =   ((v >> 0) & 0xff); \
        buf[i+1] = ((v >> 8) & 0xff); \
        buf[i+2] = ((v >> 16) & 0xff); \
        buf[i+3] = ((v >> 24) & 0xff); \
} while (0)
#define WRITE64(buf, i, v) do { \
        buf[i] =   ((v >> 0) & 0xff); \
        buf[i+1] = ((v >> 8) & 0xff); \
        buf[i+2] = ((v >> 16) & 0xff); \
        buf[i+3] = ((v >> 24) & 0xff); \
        buf[i+4] = ((v >> 32) & 0xff); \
        buf[i+5] = ((v >> 40) & 0xff); \
        buf[i+6] = ((v >> 48) & 0xff); \
        buf[i+7] = ((v >> 56) & 0xff); \
} while (0)

#define TAIL_PING         0
#define TAIL_PONG         1

#define TAIL_RANGE1       2
#define TAIL_RANGE2       3
#define TAIL_RANGE3       4
#define TAIL_RANGE4       5

#define TAIL_SYNC_BEACON  7

/* MAC frame (IEEE 802.15.4-2011)
 *
 * Frame control (2)
 * Sequence number (1)
 * Destination PAN ID (2, optional)
 * Destination Address (2 or 8, optional)
 * Source PAN ID (2, optional)
 * Source Address (2 or 8, optional)
 * Aux Security Header (5, 6, 10 or 14, optional)
 * Payload
 * FCS (2)
 *
 * Frame control:
 *
 * 0-2 Frame Tpye
 *       000 Beacon
 *       001 Data
 *       010 Ack
 *       011 MAC command
 *       100-111 Reserved
 * 3   Security Enabled (controls Aux Security Header)
 * 4   Frame Pending
 * 5   AR (Ack Request)
 * 6   PAN ID Compression (1 -> Source PAN ID == Dest PAN ID, only Dest present)
 * 7-9 Reserved
 * 10-11 Dest Addressing Mode
 *       00 PAN ID and Address fields not present
 *       01 Reserved
 *       10 Address field contains short address (16 bit)
 *       11 Address field contains extended address (64 bit)
 * 12-13 Frame Version
 *       00 802.15.4-2003
 *       01 802.15.4-2011
 *       10-11 Reserved
 * 14-15 Source Addressing Mode
 *       Same as Dest Addressing Mode
 */

typedef struct packet {
	int frame_type;
	bool security_enabled;
	bool frame_pending;
	bool ack_requested;
	bool pan_id_compress;
	int frame_version;
	uint8_t *payload;
	int len;
	uint64_t timestamp;
	uint8_t seq;
	address_t source;
	address_t dest;
} packet_t;

#define TIMESTAMP_READ(array) ((uint64_t)((array)[0]) + ((uint64_t)((array)[1]) << 8) + ((uint64_t)((array)[2]) << 16) + ((uint64_t)((array)[3]) << 24) + ((uint64_t)((array)[4]) << 32))
#define TIMESTAMP_WRITE(array, i) do { \
	    (array)[0] = i & 0xff; \
        (array)[1] = (i >> 8) & 0xff; \
        (array)[2] = (i >> 16) & 0xff; \
        (array)[3] = (i >> 24) & 0xff; \
        (array)[4] = (i >> 32) & 0xff; \
    } while (0)


/* Note that TIME refers to system time and DWTIME refers
 * to the time on the DW1000.
 */
#define DWTIME_TO_SECONDS(x) ((x)/(128*4992*100000))
#define DWTIME_TO_NANOSECONDS(x) (10000*(x)/(128*4992))
#define DWTIME_TO_PICOSECONDS(x) (10000000*(x)/(128*4992))

#define MICROSECONDS_TO_DWTIME(x) ((x)*((uint64_t)128*4992)/10)

#define TURNAROUND_DELAY MICROSECONDS_TO_DWTIME(600)

#define SPEED_OF_LIGHT 299792458

#define DWTIME_TO_MILLIMETRES(x) ((x)*SPEED_OF_LIGHT/(128*499200))


int proto_dest(uint8_t *buf, address_t *a);
int proto_source(uint8_t *buf, int offset);
void proto_header(uint8_t *buf);
void proto_txdone(void);
void proto_rxdone(void);
void proto_rxtimeout(void);
void proto_rxerror(void);
bool proto_despatch(uint8_t *buf, int len);

radio_callbacks proto_callbacks = {
		.txdone = proto_txdone,
		.rxdone = proto_rxdone,
		.rxtimeout = proto_rxtimeout,
		.rxerror = proto_rxerror
};


void proto_init(void)
{
    distance_valid = false;
    tag_packet_timeout = false;
    tag_packet_failed = false;
}

void start_rx(void)
{
	radio_rxstart(false);
}

void txdone(void)
{
//	radio_txrxoff();
	GPIO_PinOutToggle(gpioPortA, 1);

    start_rx();
	GPIO_PinOutToggle(gpioPortA, 1);
}

#if 0
void rxdone(void)
{
	int len = radio_getpayload(rxbuf, BUFLEN);
	uint8_t txbuf[BUFLEN+5] = "ACK: ";
    memcpy(txbuf+5, rxbuf, len-2);
	radio_writepayload(rxbuf, len-2, 0);
    radio_txprepare(len+5, 0, true);
    radio_txstart(false);
}
#endif

void rxdone_anchor(void)
{
	int len;
	uint8_t rxtime[5];
	uint8_t txbuf[BUFLEN+5+3];
	uint32_t txtime;
	uint64_t trx, ttx, td;

	GPIO_PinOutToggle(gpioPortA, 1); // up

	strcpy((char *)txbuf, "ACK");

	len = radio_getpayload(txbuf + 5+3, BUFLEN);
//	GPIO_PinOutToggle(gpioPortA, 1); // down

	radio_readrxtimestamp(rxtime);

//	GPIO_PinOutToggle(gpioPortA, 1); // up

	trx = TIMESTAMP_READ(rxtime);
	ttx = trx + TURNAROUND_DELAY;
	ttx = ttx & ~0x1ff;

	td = ttx - trx + device.antenna_delay_tx;

	txtime = ttx >> 8;

	TIMESTAMP_WRITE(txbuf+3, td);

//	GPIO_PinOutToggle(gpioPortA, 1); // down

    radio_writepayload(txbuf, len-2+5+3, 0);
//	GPIO_PinOutToggle(gpioPortA, 1); // up

    radio_txprepare(len+5+3, 0, true);
//	GPIO_PinOutToggle(gpioPortA, 1); // down

    radio_setstarttime(txtime);
//	GPIO_PinOutToggle(gpioPortA, 1); // up

    radio_txstart(true);
	GPIO_PinOutToggle(gpioPortA, 1); // down

//	  debug_len = len;
//    debug_rxtime = trx;
//    debug_txtime = ttx;
}


void txdone_tag(void)
{
	uint8_t txtime[5];
	GPIO_PinOutToggle(gpioPortA, 1);

	radio_readtxtimestamp(txtime);
	transmit_time = TIMESTAMP_READ(txtime);
	start_rx();

	GPIO_PinOutToggle(gpioPortA, 1);
}

uint64_t turnaround_delay;
uint64_t receive_time;

void rxdone_tag(void)
{
	int len;
	uint8_t rxtime[5];
	uint8_t buf[BUFLEN];
	int64_t td;

//	GPIO_PinOutToggle(gpioPortA, 1);

	len = radio_getpayload(buf, BUFLEN);
	(void) len;
	radio_readrxtimestamp(rxtime);
	receive_time = TIMESTAMP_READ(rxtime);
	turnaround_delay = TIMESTAMP_READ(buf+3);
	td = (receive_time - transmit_time - turnaround_delay) & ((((uint64_t)1)<<40)-1);
	/* Sign extend */
	if (td & (((uint64_t)1) << 39))
		td |= 0xFFFFFF0000000000;
	if (tag_average_running && tag_count) {
		td_sum += td;
		tag_count--;
	} else {
	    half_ping = td / 2;
	    half_ping_distance = DWTIME_TO_MILLIMETRES(half_ping);
	    distance_valid = true;
	}

//	GPIO_PinOutToggle(gpioPortA, 1);
}

void rxtimeout_tag(void)
{
	tag_packet_timeout = true;
}

void rxerror_tag(void)
{
	tag_packet_failed = true;
}

void rxtimeout(void)
{
	start_rx();
}

void rxerror(void)
{
	start_rx();
}

void proto_txdone(void)
{
	debug.in_txdone = true;
	GPIO_PinOutToggle(gpioPortA, 1);

	if (device.txtime_ptr) {
		uint8_t txtime[5];
		radio_readtxtimestamp(txtime);
		*device.txtime_ptr = TIMESTAMP_READ(txtime);
		device.txtime_ptr = NULL;
	}
	if (device.receive_after_transmit)
	    start_rx();

	GPIO_PinOutToggle(gpioPortA, 1);
	debug.in_txdone = false;
}

void proto_rxdone(void)
{
	int len;

    debug.in_rxdone = true;
	GPIO_PinOutToggle(gpioPortA, 1); // up

	len = radio_getpayload(rxbuf, BUFLEN);

#if 1
    if (!proto_despatch(rxbuf, len) && device.continuous_receive)
       	start_rx();
#else
	(void) len;
#endif

	GPIO_PinOutToggle(gpioPortA, 1); // down
    debug.in_rxdone = false;
}

void proto_rxtimeout(void)
{
	debug.in_rxtimeout = true;
	if (device.continuous_receive)
    	start_rx();
	debug.in_rxtimeout = false;
}

void proto_rxerror(void)
{
	debug.in_rxerror = true;
   	start_rx();
	debug.in_rxerror = false;
}

void tag_start(void)
{
	if (tag_average_running && (tag_count == 0)) {
		tag_average_done = true;
		return;
    }
	time_event_in(tag_start, tag_period);
//	time_event_in(tag_start, TIME_FROM_MS(200));
	radio_txstart(false);
}

void tag_with_period(int period)
{
    radio_callbacks tag_callbacks = {
    		.txdone = txdone_tag,
    		.rxdone = rxdone_tag,
    		.rxtimeout = rxtimeout_tag,
    		.rxerror = rxerror_tag
    };

	radio_setcallbacks(&tag_callbacks);

    radio_setrxtimeout(10000); // 10ms ought to do it

    /* We really should have a better tag packet here */
    char *packet = "Hello, world!";
    radio_writepayload((uint8_t *)packet, 13, 0);
    radio_txprepare(15, 0, false);

    tag_period = period;

	tag_start();
}

void tag(void)
{
	tag_with_period(TIME_FROM_SECONDS(1));
}

void tag_average(int period, int count)
{
	tag_average_done = false;
	tag_count = tag_count_initial = count;
	td_sum = 0;
	tag_average_running = true;
	tag_with_period(period);
}

void anchor(void)
{
    radio_callbacks anchor_callbacks = {
    		.txdone = txdone,
    		.rxdone = rxdone_anchor,
    		.rxtimeout = rxtimeout,
    		.rxerror = rxerror
    };

    radio_setcallbacks(&anchor_callbacks);

    radio_setrxtimeout(0);

    start_rx();
}

void stop(void)
{
    radio_callbacks callbacks = { NULL, NULL, NULL, NULL };
    radio_setcallbacks(&callbacks);
	time_event_clear(tag_start);
	time_event_clear(range_start);
    radio_txrxoff();
}

#if 1
void range_start(void)
{
	int offset;

	if (ranging.running && (ranging.count == 0)) {
		ranging.done = true;
		return;
    }

    proto_header(txbuf);
    offset = proto_dest(txbuf, &ranging.target_addr);
    offset = proto_source(txbuf, offset);

    txbuf[offset++] = TAIL_RANGE1;

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, false);

    device.txtime_ptr = &ranging.tx_stamp;

	time_event_in(range_start, ranging.period);
	radio_txstart(false);
//	write_string(".");
}

void range_with_period(address_t *addr, int period)
{
	radio_setcallbacks(&proto_callbacks);

	device.continuous_receive = false;
	device.receive_after_transmit = true;
    radio_setrxtimeout(10000); // 10ms ought to do it

    ranging.period = period;
    ranging.active = true;
    ranging.valid = false;

	ranging.tx_stamp = 0;
	ranging.rt1 = 0;
	ranging.rt2 = 0;
	ranging.tt1 = 0;
	ranging.tt2 = 0;
	ranging.time = 0;
	ranging.distance = 0;
	ranging.timeout = false;
	ranging.failed = false;

	ranging.target_addr = *addr;

	range_start();
}

void range(address_t *address)
{
	ranging.running = false;
	ranging.done = false;
	ranging.count = 0;
	ranging.count_initial = 0;
	ranging.sum = 0;

	range_with_period(address, TIME_FROM_SECONDS(1));
}

void range_average(address_t *address, int period, int count)
{
	ranging.done = false;
	ranging.count = ranging.count_initial = count;
	ranging.sum = 0;
	ranging.running = true;

	range_with_period(address, period);
}

void ranchor(void)
{
	radio_setcallbacks(&proto_callbacks);

	device.continuous_receive = true;
	device.receive_after_transmit = true;
    radio_setrxtimeout(0);

    ranging.period = 0;
    ranging.active = false;
    ranging.valid = false;

	ranging.tx_stamp = 0;
	ranging.rt1 = 0;
	ranging.rt2 = 0;
	ranging.tt1 = 0;
	ranging.tt2 = 0;
	ranging.time = 0;
	ranging.distance = 0;
	ranging.timeout = false;
	ranging.failed = false;

	ranging.running = false;
	ranging.done = false;
	ranging.count = 0;
	ranging.count_initial = 0;
	ranging.sum = 0;

    start_rx();
}
#endif

void proto_poll()
{
    if (ranging.valid || ranging.done) {
    	int64_t time;
    	int64_t mm;
    	int64_t rt1 = ranging.rt1;
    	int64_t rt2 = ranging.rt2;
    	int64_t tt1 = ranging.tt1;
    	int64_t tt2 = ranging.tt2;

    	/* Sign extend */
    	if (rt1 & (((uint64_t)1) << 39))
    		rt1 |= 0xFFFFFF0000000000;
    	if (rt2 & (((uint64_t)1) << 39))
    		rt2 |= 0xFFFFFF0000000000;
    	if (tt1 & (((uint64_t)1) << 39))
    		tt1 |= 0xFFFFFF0000000000;
    	if (tt2 & (((uint64_t)1) << 39))
    		tt2 |= 0xFFFFFF0000000000;

#if 0
    	time = (rt1 * rt2 - tt1 * tt2) /
    		   (rt1 + rt2 + tt1 + tt2);

#else
    	/* This calculation reduces the intermediate
    	 * values, so may possibly even with in 32
    	 * bit arithmetic.
    	 */
    	time = ((rt1 + tt1) * (rt2 - tt2)
		     +  (rt1 - tt1) * (rt1 + tt2))
		     / (2*(rt1 + rt2 + tt1 + tt2));
#endif
    	if (ranging.running && ranging.valid) {
    		ranging.sum += time;
    		if (ranging.count)
    			ranging.count--;
    	}

    	if (ranging.done) {
    		ranging.running = false;
    		ranging.done = false;
    		time = ranging.sum / ranging.count_initial;
    	}

    	ranging.valid = false;

    	if (!ranging.running) {
    		mm = DWTIME_TO_MILLIMETRES(time);
        	write_int(mm);
#if 0
        	{
        		int64_t time1 = rt1 - tt1;
        		int64_t time2 = rt2 - tt2;
        		int64_t mm1 = DWTIME_TO_MILLIMETRES(time1);
        		int64_t mm2 = DWTIME_TO_MILLIMETRES(time2);
        		write_string(" (");
        		write_int(mm1);
        		write_string(",");
        		write_int(mm2);
        		write_string(") - ");
        		write_int64(rt1);
        		write_string(",");
        		write_int64(rt2);
        		write_string(",");
        		write_int64(tt1);
        		write_string(",");
        		write_int64(tt2);
        	}
#endif
        	write_string("\r\n");
        }
    }

	if (tag_average_done) {
	    half_ping = td_sum / (2 * tag_count_initial);
        half_ping_distance = DWTIME_TO_MILLIMETRES(half_ping);
        distance_valid = true;
        tag_average_running = false;
        tag_packet_timeout = false;
        tag_packet_failed = false;
        tag_average_done = false;
    }

    if (distance_valid) {
        int64_t mm = half_ping_distance;
        distance_valid = false;
        write_int(mm);
#if 0
        write_string(",");
        write_int64(receive_time);
        write_string(",");
        write_int64(transmit_time);
        write_string(",");
        write_int64(turnaround_delay);
#endif
        write_string("\r\n");
    }
    if (tag_packet_timeout) {
    	tag_packet_timeout = false;
    	if (!tag_average_running)
            write_string("-----------\r\n");
    }
    if (tag_packet_failed) {
        tag_packet_failed = false;
        if (!tag_average_running)
            write_string("***ERROR***\r\n");
    }
}

void set_antenna_delay_tx(uint16_t delay)
{
    device.antenna_delay_tx = delay;
    radio_antenna_delay_tx(device.antenna_delay_tx);
}

void set_antenna_delay_rx(uint16_t delay)
{
	device.antenna_delay_rx = delay;
	radio_antenna_delay_rx(device.antenna_delay_rx);
}

void proto_header(uint8_t *buf)
{
	buf[0] = 1; /* Data frame, no security, no pending, no ACK, no PAN compression */
	buf[1] = 0x10; /* No addressing. 802.15.4-2011 frame */
	buf[2] = device.seq++;
}

int proto_source(uint8_t *buf, int offset)
{
	address_t a;
	int dest_type = (buf[1] >> 2) & 3;
	bool compressible = false;

	if (device.associated) {
		a.type = ADDR_SHORT;
		a.pan = device.pan;
		a.a.s = device.short_addr;
	} else {
		a.type = ADDR_LONG;
		a.pan = PAN_UNASSOCIATED;
		a.a.l = device.eui;
	}

    if (dest_type != ADDR_NONE) {
    	uint16_t dest_pan = READ16(buf, 3);
    	if (dest_pan == a.pan)
    		compressible = true;
    }

	buf[1] |= (a.type << 6);

	if (a.type != ADDR_NONE) {
	    if (compressible)
	    	buf[0] |= 0x40;
	    else {
	    	WRITE16(buf, offset, a.pan);
	    	offset += 2;
	    }
	}
    if (a.type == ADDR_SHORT) {
		WRITE16(buf, offset, a.a.s);
		offset += 2;
	}
	if (a.type == ADDR_LONG) {
		WRITE64(buf, offset, a.a.l);
		offset += 8;
	}

	return offset;
}

int proto_dest(uint8_t *buf, address_t *a)
{
	buf[1] |= (a->type << 2); // Destination

	int offset = 3;

	if (a->type != ADDR_NONE) {
		WRITE16(buf, offset, a->pan);
		offset += 2;
		if (a->type == ADDR_SHORT) {
			WRITE16(buf, offset, a->a.s);
			offset += 2;
		}
	    if (a->type == ADDR_LONG) {
	    	WRITE64(buf, offset, a->a.l);
	    	offset += 8;
	    }
	}

	return offset;
}

int proto_reply(uint8_t *buf, packet_t *p)
{
	int offset;

	offset = proto_dest(buf, &p->source);
	offset = proto_source(buf, offset);

	return offset;
}

bool tail_ping(packet_t *p)
{
	uint32_t txtime;
	uint64_t ttx, td;
	int pp;

	ttx = p->timestamp + TURNAROUND_DELAY;
	ttx = ttx & ~0x1ff;

	td = ttx - p->timestamp + device.antenna_delay_tx;

	txtime = ttx >> 8;

	proto_header(txbuf);
	pp = proto_reply(txbuf, p);

	txbuf[pp++] = TAIL_PONG;

	TIMESTAMP_WRITE(txbuf+pp, td);
	pp += 5;

    radio_writepayload(txbuf, pp, 0);
    radio_txprepare(pp+2, 0, true);
    radio_setstarttime(txtime);
    radio_txstart(true);

    return true;
}

bool tail_pong(packet_t *p)
{
	int64_t td;

	turnaround_delay = TIMESTAMP_READ(p->payload+1);
	td = (p->timestamp - transmit_time - turnaround_delay) & ((((uint64_t)1)<<40)-1);
	/* Sign extend */
	if (td & (((uint64_t)1) << 39))
		td |= 0xFFFFFF0000000000;
	if (tag_average_running && tag_count) {
		td_sum += td;
		tag_count--;
	} else {
	    half_ping = td / 2;
	    half_ping_distance = DWTIME_TO_MILLIMETRES(half_ping);
	    distance_valid = true;
	}

    return false;
}

bool tail_range1(packet_t *p)
{
	uint64_t ttx, td;
	int pp;

	ttx = p->timestamp + TURNAROUND_DELAY;
	ttx = ttx & ~0x1ff;

	td = ttx - p->timestamp + device.antenna_delay_tx;

	ranging.tx_stamp = ttx;

	proto_header(txbuf);
	pp = proto_reply(txbuf, p);

	txbuf[pp++] = TAIL_RANGE2;

	TIMESTAMP_WRITE(txbuf+pp, td);
	pp += 5;

    radio_writepayload(txbuf, pp, 0);
    radio_txprepare(pp+2, 0, true);
    radio_setstarttime(ttx >> 8);
    radio_txstart(true);

    return true;
}

bool tail_range2(packet_t *p)
{
	uint64_t ttx;
	int pp;

	ranging.tt1 = TIMESTAMP_READ(p->payload+1);

	ttx = p->timestamp + TURNAROUND_DELAY;
	ttx = ttx & ~0x1ff;

	ranging.rt1 = p->timestamp - ranging.tx_stamp;
	ranging.tt2 = ttx - p->timestamp;

	ranging.tx_stamp = ttx;

	proto_header(txbuf);
	pp = proto_reply(txbuf, p);

	txbuf[pp++] = TAIL_RANGE3;

    radio_writepayload(txbuf, pp, 0);
    radio_txprepare(pp+2, 0, true);
    radio_setstarttime(ttx >> 8);
    radio_txstart(true);

    return true;
}

bool tail_range3(packet_t *p)
{
	uint64_t ttx, td;
	int pp;

	ttx = p->timestamp + TURNAROUND_DELAY;
	ttx = ttx & ~0x1ff;

	td = p->timestamp - ranging.tx_stamp;

	proto_header(txbuf);
	pp = proto_reply(txbuf, p);

	txbuf[pp++] = TAIL_RANGE4;

	TIMESTAMP_WRITE(txbuf+pp, td);
	pp += 5;

    radio_writepayload(txbuf, pp, 0);
    radio_txprepare(pp+2, 0, true);
    radio_setstarttime(ttx >> 8);
    radio_txstart(true);

    return true;
}

bool tail_range4(packet_t *p)
{
	ranging.rt2 = TIMESTAMP_READ(p->payload+1);

	ranging.valid = true;

	return false;
}

bool tail_sync_beacon(packet_t *p)
{
    return false;
}

/* Return true if a packet transmitted */
bool proto_despatch(uint8_t *buf, int len)
{
	int pp;
	uint8_t rxtime[5];

    struct packet p;

#if 0
    volatile bool foo = true;
    while (foo) ;
#endif

	if (len < 3)
		/* Invalid packet */
		return false;

	radio_readrxtimestamp(rxtime);
	p.timestamp = TIMESTAMP_READ(rxtime);

	p.frame_type       = (buf[0] >> 0) & 7;
	p.security_enabled = (buf[0] >> 3) & 1;
	p.frame_pending    = (buf[0] >> 4) & 1;
	p.ack_requested    = (buf[0] >> 5) & 1;
    p.pan_id_compress  = (buf[0] >> 6) & 1;
	p.dest.type        = (buf[1] >> 2) & 3;
	p.frame_version    = (buf[1] >> 4) & 3;
	p.source.type      = (buf[1] >> 6) & 3;

	p.seq = buf[2];
	pp = 3;

	if (p.dest.type != ADDR_NONE) {
		p.dest.pan = READ16(buf, pp);
		pp += 2;
		if (p.dest.type == ADDR_SHORT) {
			p.dest.a.s = READ16(buf, pp);
			pp += 2;
		}
	    if (p.dest.type == ADDR_LONG) {
	    	p.dest.a.l = READ64(buf, pp);
	    	pp += 8;
	    }
	}
	if (p.source.type != ADDR_NONE) {
		if (p.pan_id_compress)
		    p.source.pan = p.dest.pan;
		else {
			p.source.pan = READ16(buf, pp);
			pp += 2;
		}
		if (p.source.type == ADDR_SHORT) {
			p.source.a.s = READ16(buf, pp);
			pp += 2;
		}
		if (p.source.type == ADDR_LONG) {
			p.source.a.l = READ64(buf, pp);
			pp += 8;
		}
	}
	if (p.security_enabled) {
		/* Currently unimplemented */
		return false;
#if 0
		int security_level = buf[pp] & 7;
		int key_id_mode = (buf[pp] >> 3) & 3;
		uint32_t frame_counter = READ32(buf, pp+1);
		pp += 5;
		uint8_t *key_id_ptr = pp;
		pp += ((const int[]){0, 1, 5, 9})[key_id_mode];
#endif
	}

	/* We haven't checked the length properly while parsing the addresses.
	 * For the sake of efficiency we won't do that, but this does mean that
	 * we are assuming that even if the length given is too short for the
	 * indicated packet, it is at least valid memory.
	 * We will reject the packet without doing anything dangerous with the
	 * invalid header, even though we have potentially read that memory.
	 */
	if (len < pp)
		return false;

	len -= pp;
	p.payload = buf+pp;

	switch (p.frame_type) {
	case 0:
		/* Beacon */
		break;
	case 1:
		/* Data */
		switch (buf[pp]) {
		case TAIL_PING:
			return tail_ping(&p);
		case TAIL_PONG:
			return tail_pong(&p);
		case TAIL_RANGE1:
			return tail_range1(&p);
		case TAIL_RANGE2:
			return tail_range2(&p);
		case TAIL_RANGE3:
			return tail_range3(&p);
		case TAIL_RANGE4:
			return tail_range4(&p);
		case TAIL_SYNC_BEACON:
			return tail_sync_beacon(&p);
		}
		break;
	case 2:
		/* Ack */
		break;
	case 3:
		/* MAC command */
		break;
	default:
		/* Reserved */
		break;
	}
	return false;
}
