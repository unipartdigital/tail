/* proto.c */

#include "radio.h"
#include "uart.h"
#include "time.h"
#include "proto.h"
#include "config.h"

#include "em_gpio.h"

#define BUFLEN 1024
#define HEADER_MAX 37

/* Note that TIME refers to system time and DWTIME refers
 * to the time on the DW1000.
 */
#define DWTIME_TO_SECONDS(x) ((x)/(128*4992*100000))
#define DWTIME_TO_NANOSECONDS(x) (10000*(x)/(128*4992))
#define DWTIME_TO_PICOSECONDS(x) (10000000*(x)/(128*4992))

#define MICROSECONDS_TO_DWTIME(x) ((x)*((uint64_t)128*4992)/10)

/* This is the default value */
#define TURNAROUND_DELAY MICROSECONDS_TO_DWTIME(700)

#define SPEED_OF_LIGHT 299792458

#define DWTIME_TO_MILLIMETRES(x) ((x)*SPEED_OF_LIGHT/(128*499200))


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
	volatile bool radio_active;
	bool radio_sleeping;
	uint8_t volts;
	uint8_t temp;
	uint8_t volts_cal;
	uint8_t temp_cal;
	uint64_t turnaround_delay;
	uint32_t rxtimeout;
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
		.receive_after_transmit = false,
		.radio_active = false,
		.radio_sleeping = false,
		.volts = 0,
		.temp = 0,
		.volts_cal = 0,
		.temp_cal = 0,
		.turnaround_delay = TURNAROUND_DELAY,
		.rxtimeout = 10000
};

typedef struct {
	address_t target_mac_addr;
	ipv6_addr_t target_ipv6_addr;
	uint16_t source_port;
	uint16_t dest_port;
	int period;
} tag_data_t;

#define DEFAULT_IPV6_ADDR {0xff, 0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}
#define DEFAULT_TARGET_ADDR {.type = ADDR_SHORT, .pan = PAN_BROADCAST, .a.s = 0xffff}
ipv6_addr_t default_ipv6_addr = DEFAULT_IPV6_ADDR;
address_t default_target_addr = DEFAULT_TARGET_ADDR;
#define DEFAULT_SOURCE_PORT 0xf0b0
#define DEFAULT_DEST_PORT 0xf0b0

tag_data_t tag_data = {
		.target_mac_addr = DEFAULT_TARGET_ADDR,
        .target_ipv6_addr = DEFAULT_IPV6_ADDR,
		.source_port = 0xf0b0,
        .dest_port = 0xf0b0,
        .period = TIME_FROM_SECONDS(1)
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

#define TAIL_HEADER_ACCEL   0x80
#define TAIL_HEADER_LISTEN  0x40
#define TAIL_HEADER_BATTERY 0x20
#define TAIL_HEADER_CONFIG  0x10

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


int proto_dest(uint8_t *buf, address_t *a);
int proto_source(uint8_t *buf, int offset);
void proto_header(uint8_t *buf);
void proto_txdone(void);
void proto_rxdone(void);
void proto_rxtimeout(void);
void proto_rxerror(void);
bool proto_despatch(uint8_t *buf, int len);
void proto_prepare(void);


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

    device.eui = 0;
    (void) config_get(config_key_eui, (uint8_t *)&device.eui, sizeof(device.eui));

    device.associated = (config_get8(config_key_associated) != 0);
    device.short_addr = config_get16(config_key_short_addr);
    device.pan = 0;
    if (config_get(config_key_pan, (uint8_t *)&device.pan, sizeof(device.pan)) <= 0)
    	device.pan = PAN_UNASSOCIATED;

    device.radio_active = false;
    device.radio_sleeping = false;

    radio_read_adc_cal(&device.volts_cal, &device.temp_cal);

    time_early_wakeup(proto_prepare, PROTO_PREPARETIME);
}

void start_rx(void)
{
	device.radio_active = true;
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
	ttx = trx + device.turnaround_delay;
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
	device.radio_active = false;

//	GPIO_PinOutToggle(gpioPortA, 1);
}

void rxtimeout_tag(void)
{
	tag_packet_timeout = true;
	device.radio_active = false;
}

void rxerror_tag(void)
{
	tag_packet_failed = true;
	device.radio_active = false;
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
	else
		device.radio_active = false;

	GPIO_PinOutToggle(gpioPortA, 1);
	debug.in_txdone = false;
}

void proto_rxdone(void)
{
	int len;

    debug.in_rxdone = true;
	GPIO_PinOutToggle(gpioPortA, 1); // up

	len = radio_getpayload(rxbuf, BUFLEN);

    if (!proto_despatch(rxbuf, len) && device.continuous_receive)
       	start_rx();

	GPIO_PinOutToggle(gpioPortA, 1); // down
    debug.in_rxdone = false;
}

void proto_rxtimeout(void)
{
	debug.in_rxtimeout = true;
	if (device.continuous_receive)
    	start_rx();
	else
		device.radio_active = false;
	debug.in_rxtimeout = false;
}

void proto_rxerror(void)
{
	debug.in_rxerror = true;
   	start_rx();
	debug.in_rxerror = false;
}

void proto_turnaround_delay(uint32_t us)
{
	device.turnaround_delay = MICROSECONDS_TO_DWTIME(us);
}

/* time is in units of 1.0256 us (512/499.2MHz) */
void proto_rx_timeout(uint32_t time)
{
	device.rxtimeout = time;
}

void tag_start(void)
{
	if (tag_average_running && (tag_count == 0)) {
		tag_average_done = true;
		return;
    }
	time_event_in(tag_start, tag_period);
//	time_event_in(tag_start, TIME_FROM_MS(200));
	device.radio_active = true;
	radio_txstart(false);
}

void tag_with_period(int period)
{
	proto_prepare();
	radio_callbacks tag_callbacks = {
    		.txdone = txdone_tag,
    		.rxdone = rxdone_tag,
    		.rxtimeout = rxtimeout_tag,
    		.rxerror = rxerror_tag
    };

	radio_setcallbacks(&tag_callbacks);

    radio_setrxtimeout(device.rxtimeout);

    /* We really should have a better tag packet here */
    char *packet = "Hello, world!";
    radio_writepayload((uint8_t *)packet, 13, 0);
    radio_txprepare(15, 0, false);

    tag_period = period;

	tag_start();
}

int ipv6_header(uint8_t *buf, int offset, ipv6_addr_t a)
{
	int dam = 0;
	if ((a[0] == 0xff) &&
			(a[2] == 0) && (a[3] == 0) && (a[4] == 0) && (a[5] == 0) &&
			(a[6] == 0) && (a[7] == 0) && (a[8] == 0) && (a[9] == 0) &&
			(a[10] == 0)) {
	    dam++;
	    if ((a[11] == 0) && (a[12] == 0)) {
	    	dam++;
			if ((a[1] == 2) && (a[13] == 0) && (a[14] == 0)) {
				dam++;
			}
	    }
	}
    /* compressed IPv6 header */
    /* XXX this will need revisiting to efficiently address non-multicast addresses */
    buf[offset++] = 0x7f; /* iphc header TF=3, NH=1, HLIM=3 */
    buf[offset++] = 0x38+dam; /* CID=0, SAC=0, SAM=3, M=1, DAC=0, DAM=dam */

    switch (dam) {
    case 0:
    	for (int i = 0; i < 16; i++)
    	    buf[offset++] = a[i];
    	break;
    case 1:
    	buf[offset++] = a[1];
    	buf[offset++] = a[11];
    	buf[offset++] = a[12];
    	buf[offset++] = a[13];
    	buf[offset++] = a[14];
    	buf[offset++] = a[15];
    	break;
    case 2:
    	buf[offset++] = a[1];
    	buf[offset++] = a[13];
    	buf[offset++] = a[14];
    	buf[offset++] = a[15];
    	break;
    case 3:
    	buf[offset++] = a[15];
    	break;
    }

    return offset;
}

int ipv6_udp_header(uint8_t *buf, int offset, uint16_t source_port, uint16_t dest_port)
{
	int p;

	if (((source_port & 0xfff0) == 0xf0b0) && ((dest_port & 0xfff0) == 0xf0b0))
		p = 3;
	else if ((source_port & 0xff00) == 0xf000)
		p = 2;
	else if ((dest_port & 0xff00) == 0xf000)
		p = 1;
	else
		p = 0;

    /* compressed UDP header */
    buf[offset++] = 0xf0 + p; /* HC_UDP, C=0, P=p */

    if (p == 3) {
    	buf[offset++] = ((source_port & 0x0f) << 4) | (dest_port & 0x0f);
    } else {
    	if (p != 2)
    	    buf[offset++] = source_port >> 8;
    	buf[offset++] = source_port & 0xff;
    	if (p != 1)
    	    buf[offset++] = dest_port >> 8;
    	buf[offset++] = dest_port & 0xff;
    }

    buf[offset++] = 0x00; /* Placeholder for UDP checksum 1 */
    buf[offset++] = 0x00; /* Placeholder for UDP checksum 2 */

    return offset;
}

void ipv6_udp_checksum(uint8_t *buf, address_t *mac_addr, ipv6_addr_t ipv6_addr, uint16_t source_port, uint16_t dest_port, int udp_offset, int offset)
{
	uint32_t checksum = 0;
	int payload_offset = udp_offset + 3;
	switch (buf[udp_offset] & 3) {
	case 0:
		payload_offset += 4;
		break;
	case 1:
	case 2:
		payload_offset += 3;
		break;
	case 3:
		payload_offset += 1;
		break;
	}
	int length = offset - payload_offset;

	/* 128 bit source address */
	checksum += 0xfe80; /* Link local prefix */
	switch (mac_addr->type) {
	case ADDR_SHORT:
		checksum += mac_addr->pan ^ 0x0200; /* U/L bit */
		checksum += 0x00ff;
		checksum += 0xfe00;
	    checksum += mac_addr->a.s;
		break;
	case ADDR_LONG:
		checksum += ((mac_addr->a.l >> 48) & 0xffff) ^ 0x0200; /* U/L bit */
		checksum += ((mac_addr->a.l >> 32) & 0xffff);
		checksum += ((mac_addr->a.l >> 16) & 0xffff);
		checksum += (mac_addr->a.l & 0xffff);
		break;
	}
	/* 128 bits dest address */
	for (int i = 0; i < 16; i += 2)
	    checksum += ((uint16_t)(ipv6_addr[i]) << 8) + ipv6_addr[i+1];
	/* upper-layer packet length plus uncompressed UDP header length */
	checksum += length + 8;

	/* next header */
	checksum += 17; /* UDP next header */

	/* UDP header */
    checksum += source_port;
	checksum += dest_port;
	checksum += length + 8;

	for (int i = 0; i < (length & ~1); i += 2) {
		checksum += ((buf[payload_offset + i] << 8) | buf[payload_offset + i + 1]);
	}
	if (length & 1)
		checksum += (buf[payload_offset + length-1] << 8);

	checksum = (checksum & 0xffff) + (checksum >> 16);
	checksum = (checksum & 0xffff) + (checksum >> 16);

	checksum = ~checksum;

	txbuf[payload_offset-2] = (checksum >> 8) & 0xff;
	txbuf[payload_offset-1] = (checksum >> 0) & 0xff;
}

void tagipv6_start(void)
{
    int offset, udp_offset;
    uint8_t voltage, temperature;

    time_event_in(tagipv6_start, tag_data.period);

    proto_header(txbuf);
    offset = proto_dest(txbuf, &tag_data.target_mac_addr);
    offset = proto_source(txbuf, offset);
    offset = ipv6_header(txbuf, offset, tag_data.target_ipv6_addr);
    udp_offset = offset;
    offset = ipv6_udp_header(txbuf, offset, tag_data.source_port, tag_data.dest_port);

    /* payload goes here */
    txbuf[offset++] = TAIL_HEADER_BATTERY; /* Tail status flags */

    radio_wakeup_adc_readings(&voltage, &temperature);

    txbuf[offset++] = voltage; /* Battery state */
    txbuf[offset++] = temperature; /* Temperature */
    txbuf[offset++] = device.volts_cal;
    txbuf[offset++] = device.temp_cal;

    address_t source_mac_addr;

    source_mac_addr.pan = device.pan;
    if (device.associated) {
        source_mac_addr.type = ADDR_SHORT;
        source_mac_addr.a.s = device.short_addr;
    } else {
    	source_mac_addr.type = ADDR_LONG;
        source_mac_addr.a.l = device.eui;
    }

    ipv6_udp_checksum(txbuf, &source_mac_addr, tag_data.target_ipv6_addr, tag_data.source_port, tag_data.dest_port, udp_offset, offset);

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, false);

	device.radio_active = true;

	radio_txstart(false);
}

void tagipv6_txdone(void)
{
	device.radio_active = false;
}

void tagipv6_with_period(int period)
{
	proto_prepare();
    radio_callbacks tag_callbacks = {
    		.txdone = tagipv6_txdone,
    		.rxdone = NULL,
    		.rxtimeout = NULL,
    		.rxerror = NULL
    };

	radio_setcallbacks(&tag_callbacks);

	tag_data.target_mac_addr = default_target_addr;
    /* Do we want to be able to direct this packet differently at the MAC layer? */

	memcpy(tag_data.target_ipv6_addr, default_ipv6_addr, sizeof(ipv6_addr_t));
	(void) config_get(config_key_tag_target_addr, tag_data.target_ipv6_addr, 16);

	tag_data.source_port = DEFAULT_SOURCE_PORT;
	tag_data.dest_port = DEFAULT_DEST_PORT;

	(void) config_get(config_key_tag_source_port, (uint8_t *)&tag_data.source_port, sizeof(tag_data.source_port));
	(void) config_get(config_key_tag_dest_port, (uint8_t *)&tag_data.dest_port, sizeof(tag_data.dest_port));

	tag_data.period = period;

	tagipv6_start();
}

void tagipv6(void)
{
	int period = 0;
	if (config_get(config_key_tag_period, (uint8_t *)&period, sizeof(int)) <= 0)
		period = 1000;
	tagipv6_with_period(TIME_FROM_MS(period));
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
	proto_prepare();
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
	time_event_clear(tagipv6_start);
    radio_txrxoff();
    device.radio_active = false;
}

#if 1
void range_start(void)
{
	int offset;

	if (ranging.running && (ranging.count == 0)) {
		ranging.done = true;
		device.radio_active = false;
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
	device.radio_active = true;
	radio_txstart(false);
}

void range_with_period(address_t *addr, int period)
{
	proto_prepare();
	radio_setcallbacks(&proto_callbacks);

	device.continuous_receive = false;
	device.receive_after_transmit = true;
    radio_setrxtimeout(device.rxtimeout);

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
	proto_prepare();
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

	device.radio_active = true;

    start_rx();
}
#endif

void proto_poll()
{
	bool valid = ranging.valid;

    if (valid || ranging.done) {
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
    	if (ranging.running && valid) {
    		ranging.sum += time;
    		if (ranging.count)
    			ranging.count--;
    	}

    	if (ranging.done) {
    		ranging.running = false;
    		ranging.done = false;
    		time = ranging.sum / ranging.count_initial;
    	}

    	if (valid)
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
        	write_string("!\r\n");
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
        write_string("?\r\n");
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
    if (!device.radio_active && !device.radio_sleeping) {
    	if (time_to_next_event() >= PROTO_PREPARETIME) {
    	    device.radio_sleeping = true;
    	    radio_configsleep(RADIO_SLEEP_CONFIG | RADIO_SLEEP_TANDV, RADIO_SLEEP_WAKE_WAKEUP | RADIO_SLEEP_ENABLE);
    	    radio_entersleep();
    	}
    }
}

/* Called when the radio may be asleep and we need to get ready for action */
void proto_prepare(void)
{
    if (!device.radio_sleeping)
    	return;
    device.radio_sleeping = false;
    /* Keep the radio awake until it is used */
    device.radio_active = true;
    radio_wakeup();
    radio_wakeup_adc_readings(&device.volts, &device.temp);
}

/* Like proto_prepare, but we want to perform an immediate operation and don't
 * need to keep the radio awake after the next poll
 */
void proto_prepare_immediate(void)
{
    if (!device.radio_sleeping)
    	return;
    device.radio_sleeping = false;
    radio_wakeup();
    radio_wakeup_adc_readings(&device.volts, &device.temp);
}

int proto_volts(void)
{
	int v = device.volts;
	return 1000 * (v - device.volts_cal) / 173 + 3300;
}

int proto_temp(void)
{
	int t = device.temp;
	return 1140 * (t - device.temp_cal) + 23000;
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

	ttx = p->timestamp + device.turnaround_delay;
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

	ttx = p->timestamp + device.turnaround_delay;
	ttx = ttx & ~0x1ff;

	td = ttx - p->timestamp + device.antenna_delay_tx;

	ranging.tx_stamp = ttx + device.antenna_delay_tx;

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

	ttx = p->timestamp + device.turnaround_delay;
	ttx = ttx & ~0x1ff;

	ranging.rt1 = p->timestamp - ranging.tx_stamp;
	ranging.tt2 = ttx - p->timestamp + device.antenna_delay_tx;

	ranging.tx_stamp = ttx + device.antenna_delay_tx;

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

	ttx = p->timestamp + device.turnaround_delay;
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
			write_string("p");
			return tail_ping(&p);
		case TAIL_PONG:
			write_string("o");
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
