/* proto.c */

#include "radio.h"
#include "uart.h"
#include "time.h"
#include "proto.h"
#include "config.h"
#include "accel.h"
#include "battery.h"

#include "em_gpio.h"

#include "byteorder.h"

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
	uint8_t radio_volts;
	uint8_t radio_temp;
	uint8_t radio_volts_cal;
	uint8_t radio_temp_cal;
	uint32_t adc_volts;
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
		.radio_volts = 0,
		.radio_temp = 0,
		.radio_volts_cal = 0,
		.radio_temp_cal = 0,
		.adc_volts = 0,
		.turnaround_delay = TURNAROUND_DELAY,
		.rxtimeout = 10000
};

typedef struct {
	address_t target_mac_addr;
	int period_active;
	int period_idle;
	int transition_time;
	uint32_t last_event;
	bool active;
	bool two_way;
	uint64_t tx_stamp;
	uint32_t two_way_window;
} tag_data_t;

#define DEFAULT_TARGET_ADDR {.type = ADDR_SHORT, .pan = PAN_BROADCAST, .a.s = 0xffff}
address_t default_target_addr = DEFAULT_TARGET_ADDR;

tag_data_t tag_data = {
		.target_mac_addr = DEFAULT_TARGET_ADDR,
        .period_active = TIME_FROM_SECONDS(1),
		.period_idle = TIME_FROM_SECONDS(100),
		.transition_time = TIME_FROM_SECONDS(10),
		.active = false,
		.two_way = false,
		.tx_stamp = 0,
		.two_way_window = 0,
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

#define TAIL_MAGIC          0x37

#define TAIL_HEADER_EXTRA   0x80
#define TAIL_HEADER_LISTEN  0x40
#define TAIL_HEADER_BATTERY 0x20
#define TAIL_HEADER_ACCEL   0x10
#define TAIL_HEADER_CONFIG  (unimplemented)
#define TAIL_HEADER_TIMING  0x08
#define TAIL_HEADER_DEBUG   0x01

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
	int hlen;
} packet_t;

#define TIMESTAMP_READ(array) ((uint64_t)((array)[0]) + ((uint64_t)((array)[1]) << 8) + ((uint64_t)((array)[2]) << 16) + ((uint64_t)((array)[3]) << 24) + ((uint64_t)((array)[4]) << 32))
#define TIMESTAMP_WRITE(array, i) do { \
	    (array)[0] = i & 0xff; \
        (array)[1] = (i >> 8) & 0xff; \
        (array)[2] = (i >> 16) & 0xff; \
        (array)[3] = (i >> 24) & 0xff; \
        (array)[4] = (i >> 32) & 0xff; \
    } while (0)

#define TIMESTAMP_READ_BE(array) ((uint64_t)((array)[4]) + ((uint64_t)((array)[3]) << 8) + ((uint64_t)((array)[2]) << 16) + ((uint64_t)((array)[1]) << 24) + ((uint64_t)((array)[0]) << 32))
#define TIMESTAMP_WRITE_BE(array, i) do { \
	    (array)[4] = i & 0xff; \
        (array)[3] = (i >> 8) & 0xff; \
        (array)[2] = (i >> 16) & 0xff; \
        (array)[1] = (i >> 24) & 0xff; \
        (array)[0] = (i >> 32) & 0xff; \
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
address_t my_mac_address(void);


radio_callbacks proto_callbacks = {
		.txdone = proto_txdone,
		.rxdone = proto_rxdone,
		.rxtimeout = proto_rxtimeout,
		.rxerror = proto_rxerror
};

#define BATTERY_FILTER 4

void proto_update_battery(void)
{
    uint16_t volts = battery_read();
    if (device.adc_volts == 0)
    	device.adc_volts = volts << BATTERY_FILTER;
    else {
    	device.adc_volts = device.adc_volts - (device.adc_volts >> BATTERY_FILTER) + volts;
    }
}

uint16_t proto_battery_volts(void)
{
	return device.adc_volts >> BATTERY_FILTER;
}

void proto_init(void)
{
    device.eui = 0;
    (void) config_get(config_key_eui, (uint8_t *)&device.eui, sizeof(device.eui));

    device.associated = (config_get8(config_key_associated) != 0);
    device.short_addr = config_get16(config_key_short_addr);
    device.pan = 0;
    if (config_get(config_key_pan, (uint8_t *)&device.pan, sizeof(device.pan)) <= 0)
    	device.pan = PAN_UNASSOCIATED;

    device.radio_active = false;
    device.radio_sleeping = false;

    radio_read_adc_cal(&device.radio_volts_cal, &device.radio_temp_cal);
    battery_init();
    proto_update_battery();

    time_early_wakeup(proto_prepare, PROTO_PREPARETIME);
}

void start_rx(void)
{
	device.radio_active = true;
	radio_rxstart(false);
}

uint64_t turnaround_delay;
uint64_t receive_time;

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

void tagipv6_set_event(uint32_t now)
{
	int period;

	/* XXX there's a very occasional wraparound problem here. */
	int time_diff = time_sub(now, accel_last_activity());
	if ((time_diff >= 0) && (time_diff < tag_data.transition_time)) {
		period = tag_data.period_active;
	} else {
		period = tag_data.period_idle;
	}

    uint32_t time = time_add(tag_data.last_event, period);
    time_event_at(tagipv6_start, time);
}

address_t my_mac_address(void)
{
	address_t mac_addr;
    mac_addr.pan = device.pan;
    if (device.associated) {
        mac_addr.type = ADDR_SHORT;
        mac_addr.a.s = device.short_addr;
    } else {
    	mac_addr.type = ADDR_LONG;
        mac_addr.a.l = device.eui;
    }
    return mac_addr;
}

void tagipv6_start(void)
{
    int offset;
    uint8_t voltage, temperature;

    tag_data.active = true;

    tag_data.last_event = time_now();
    tagipv6_set_event(tag_data.last_event);

    proto_header(txbuf);
    offset = proto_dest(txbuf, &tag_data.target_mac_addr);
    offset = proto_source(txbuf, offset);
    txbuf[offset++] = TAIL_MAGIC;

    int header = TAIL_HEADER_BATTERY | TAIL_HEADER_DEBUG;
    if (device.receive_after_transmit)
    	header |= TAIL_HEADER_LISTEN;

    /* payload goes here */
    txbuf[offset++] = header;

    radio_wakeup_adc_readings(&voltage, &temperature);

    uint16_t volts = proto_battery_volts();

    txbuf[offset++] = battery_state(volts);

    txbuf[offset++] = 6; /* Length of debug field */
    txbuf[offset++] = voltage; /* Battery state */
    txbuf[offset++] = temperature; /* Temperature */
    txbuf[offset++] = device.radio_volts_cal;
    txbuf[offset++] = device.radio_temp_cal;
    txbuf[offset++] = volts & 0xff;
    txbuf[offset++] = volts >> 8;

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, false);
    radio_setrxtimeout(device.rxtimeout);

    device.txtime_ptr = &tag_data.tx_stamp;
	device.radio_active = true;

	radio_txstart(false);
}

void tagipv6_with_period(int period, int period_idle, int transition_time)
{
	proto_prepare();

	radio_setcallbacks(&proto_callbacks);

	tag_data.target_mac_addr = default_target_addr;
    /* Do we want to be able to direct this packet differently at the MAC layer? */

	(void) config_get(config_key_tag_two_way, (uint8_t *)&tag_data.two_way, sizeof(tag_data.two_way));

	tag_data.period_active = period;
	tag_data.period_idle = period_idle;
	tag_data.transition_time = transition_time;

	device.receive_after_transmit = tag_data.two_way;
	device.continuous_receive = false;

	tagipv6_start();
}

void tagipv6(void)
{
	uint32_t period_active = 0;
	uint32_t period_idle = 0;
	uint32_t transition_time = 0;
	if (config_get(config_key_tag_period, (uint8_t *)&period_active, sizeof(int)) <= 0)
		period_active = 1000;
	if (config_get(config_key_tag_period_idle, (uint8_t *)&period_idle, sizeof(int)) <= 0)
		period_idle = 100000;
	if (config_get(config_key_tag_transition_time, (uint8_t *)&transition_time, sizeof(int)) <= 0)
		transition_time = 10;
	tagipv6_with_period(TIME_FROM_MS((uint64_t)period_active), TIME_FROM_MS((uint64_t)period_idle), TIME_FROM_SECONDS((uint64_t)transition_time));
}

void stop(void)
{
    radio_callbacks callbacks = { NULL, NULL, NULL, NULL };
    radio_setcallbacks(&callbacks);
	time_event_clear(tagipv6_start);
    radio_txrxoff();
    device.radio_active = false;
    tag_data.active = false;
}

void proto_poll()
{
    if (accel_interrupt_fired()) {
#if 0
    	write_string("Movement\r\n");
#endif
    	if (tag_data.active)
    	    tagipv6_set_event(time_now());
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
    proto_update_battery();
    radio_wakeup();
    radio_wakeup_adc_readings(&device.radio_volts, &device.radio_temp);
}

/* Like proto_prepare, but we want to perform an immediate operation and don't
 * need to keep the radio awake after the next poll
 */
void proto_prepare_immediate(void)
{
    if (!device.radio_sleeping)
    	return;
    device.radio_sleeping = false;
    proto_update_battery();
    radio_wakeup();
    radio_wakeup_adc_readings(&device.radio_volts, &device.radio_temp);
}

int proto_volts(void)
{
	int v = device.radio_volts;
	return 1000 * (v - device.radio_volts_cal) / 173 + 3300;
}

int proto_temp(void)
{
	int t = device.radio_temp;
	return 1140 * (t - device.radio_temp_cal) + 23000;
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

bool tail_timing(packet_t *p, int hlen)
{
	uint64_t ttx, td1, td2;
	int offset;

	ttx = p->timestamp + device.turnaround_delay;
	ttx = ttx & ~0x1ff;

	td1 = p->timestamp - tag_data.tx_stamp;
	td2 = ttx - tag_data.tx_stamp + device.antenna_delay_tx;

	proto_header(txbuf);
	offset = proto_reply(txbuf, p);

    txbuf[offset++] = TAIL_MAGIC;

	txbuf[offset++] = TAIL_HEADER_TIMING;

	TIMESTAMP_WRITE_BE(txbuf+offset, td1);
	offset += 5;
	TIMESTAMP_WRITE_BE(txbuf+offset, td2);
	offset += 5;

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, true);
    radio_setstarttime(ttx >> 8);
    radio_txstart(true);

    return true;
}

bool tagipv6_rx(packet_t *p)
{
    if (p->payload[0] != TAIL_MAGIC)
    	return false;
    p->hlen = 1;

	/* Decode tail packet and despatch */
	int tail_header = p->payload[p->hlen];

#if 0
	if (tail_header & TAIL_HEADER_CONFIG) {
		/* XXX we need to implement this */
		// tail_config(p, hlen);
		return false;
	}
#endif

	if (tail_header & TAIL_HEADER_TIMING) {
		return tail_timing(p, p->hlen);
	}

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
	/* 2 bytes of CRC follow the payload */
	p.len = len - 2;

	/* Here's a good place to check that the packet is indeed for us. */
	if (p.dest.type != ADDR_NONE)
		if ((p.dest.pan != device.pan) && (p.dest.pan != PAN_BROADCAST))
			return false;

	if (p.dest.type == ADDR_SHORT)
		if ((p.dest.a.s != device.short_addr) && (p.dest.a.s != ADDR_SHORT_BROADCAST))
			return false;

	if (p.dest.type == ADDR_LONG)
		if (p.dest.a.l != device.eui)
			return false;

	switch (p.frame_type) {
	case 0:
		/* Beacon */
		break;
	case 1:
		/* Data */
		switch (buf[pp]) {
		case TAIL_MAGIC:
			return tagipv6_rx(&p);
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
