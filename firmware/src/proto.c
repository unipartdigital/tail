/* proto.c */

#include "entropy.h"
#include "radio.h"
#include "uart.h"
#include "time.h"
#include "proto.h"
#include "config.h"
#include "accel.h"
#include "battery.h"
#include "timer.h"
#include "lfsr.h"
#include "event.h"

#include "em_gpio.h"

#include "byteorder.h"

#define BUFLEN 1024
#define HEADER_MAX 37

/* Note that TIME refers to system time and DWTIME refers
 * to the time on the DW1000.
 */

#define DWCLOCK (499200000)

#define DWTIME_TO_SECONDS(x) ((x)/((uint64_t)128*4992*100000))
#define DWTIME_TO_NANOSECONDS(x) (10000*(x)/(128*4992))
#define DWTIME_TO_PICOSECONDS(x) (10000000*(x)/(128*4992))

#define MICROSECONDS_TO_DWTIME(x) ((x)*((uint64_t)128*4992)/10)

#define DWTIME_SUB(x, y) (((x) - (y)) & 0xffffffffff)
#define DWTIME_ADD(x, y) (((x) + (y)) & 0xffffffffff)

#define RADIO_ALIGN(x) ((x) & ~0x1ff)

/* This is the default value */
#define TURNAROUND_DELAY MICROSECONDS_TO_DWTIME(700)

#define RX_TIMEOUT 10000
#define RX_DELAY 700

#define SPEED_OF_LIGHT 299792458

#define DWTIME_TO_MILLIMETRES(x) ((x)*SPEED_OF_LIGHT/(128*499200))

/* Periods in nominal ms */
#define PERIOD_DEFAULT_ACTIVE  1000
#define PERIOD_DEFAULT_IDLE  100000
#define PERIOD_BATTERY_FLAT  600000


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
	bool receive_after_transmit;
	volatile bool radio_active;
	bool radio_sleeping;
	bool just_woken;
	uint8_t radio_volts;
	uint8_t radio_temp;
	uint8_t radio_volts_cal;
	uint8_t radio_temp_cal;
	uint32_t adc_volts;
	uint32_t adc_validity_counter;
	uint64_t turnaround_delay;
	uint32_t rxtimeout;
	uint64_t rxdelay;
	bool reset_requested;
	uint64_t rxstarttime;
	uint64_t rxendtime;
	uint32_t rxnumerator;
	uint64_t rxdenominator;
	uint16_t rxtimer;
	uint32_t uptime_blinks;
	uint32_t radio_starttime;
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
		.receive_after_transmit = false,
		.radio_active = false,
		.radio_sleeping = false,
		.just_woken = false,
		.radio_volts = 0,
		.radio_temp = 0,
		.radio_volts_cal = 0,
		.radio_temp_cal = 0,
		.adc_volts = 0,
		.adc_validity_counter = 0,
		.turnaround_delay = TURNAROUND_DELAY,
		.rxtimeout = RX_TIMEOUT,
		.rxdelay = RX_DELAY,
		.reset_requested = false,
		.rxstarttime = 0,
		.rxendtime = 0,
		.rxnumerator = 0,
		.rxdenominator = 0,
		.rxtimer = 0,
		.uptime_blinks = 0,
		.radio_starttime = 0
};

#define MAX_ANCHORS 8

typedef struct {
	address_t address;
	uint64_t rx_stamp;
} anchor_ranging_t;

typedef struct packet packet_t;

typedef struct {
	address_t target_mac_addr;
	int period_active;
	int period_idle;
	int transition_time;
	int listen_period;
	uint32_t last_event;
	uint32_t last_receive_window;
	bool active;
	uint64_t tx_stamp;
	uint64_t last_stamp;
	anchor_ranging_t anchors[MAX_ANCHORS];
	int anchors_heard;
	int max_anchors;
	int min_responses;
	int responses_sent;
	bool idle;
	bool ranging_aborted;
	bool tx_temperature;
	bool tx_battery_voltage;
	bool tx_radio_voltage;
	bool tx_uptime_blinks;
	uint16_t jitter_active;
	uint16_t jitter_idle;
} tag_data_t;

#define DEFAULT_TARGET_ADDR {.type = ADDR_SHORT, .pan = PAN_BROADCAST, .a.s = 0xffff}
address_t default_target_addr = DEFAULT_TARGET_ADDR;

tag_data_t tag_data = {
		.target_mac_addr = DEFAULT_TARGET_ADDR,
        .period_active = TIME_FROM_SECONDS(1),
		.period_idle = TIME_FROM_SECONDS(100),
		.transition_time = TIME_FROM_SECONDS(10),
		.listen_period = 0,
		.active = false,
		.tx_stamp = 0,
		.anchors_heard = 0,
		.max_anchors = 0,
		.min_responses = 0,
		.responses_sent = 0,
		.idle = false,
		.ranging_aborted = false
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

#define TAIL_MAGIC                          0x37
#define TAIL_MAGIC_ENCRYPTED                0x38
#define TAIL_MAGIC_RESET_REQUEST            0xcafe
#define TAIL_MAGIC_RESET_RESPONSE           0xdada

#define TAIL_FRAME_BLINK                    0x00
#define TAIL_FRAME_BLINK_IV                 0x08
#define TAIL_FRAME_BLINK_IE                 0x04
#define TAIL_FRAME_BLINK_EIE                0x02

#define TAIL_FRAME_ANCHOR_BEACON            0x10

#define TAIL_FRAME_RANGING_REQUEST          0x20
#define TAIL_FRAME_RANGING_RESPONSE         0x30
#define TAIL_FRAME_RANGING_RESPONSE_OWR     0x08

#define TAIL_FRAME_CONFIG_REQUEST           0x40
#define TAIL_FRAME_CONFIG_RESPONSE          0x50

#define TAIL_FRAME_CONFIG_RESET             0x00
#define TAIL_FRAME_CONFIG_ENUMERATE         0x01
#define TAIL_FRAME_CONFIG_READ              0x02
#define TAIL_FRAME_CONFIG_WRITE             0x03
#define TAIL_FRAME_CONFIG_DELETE            0x04
#define TAIL_FRAME_CONFIG_SALT              0x05
#define TAIL_FRAME_CONFIG_TEST              0x0f

#define TAIL_FLAGS_LISTEN                   0x80
#define TAIL_FLAGS_ACCEL                    0x40
#define TAIL_FLAGS_DCIN                     0x20
#define TAIL_FLAGS_SALT                     0x10

#define TAIL_IE_BATTERY                     0x00
#define TAIL_IE_RADIO_VOLTAGE               0x01
#define TAIL_IE_TEMPERATURE                 0x02
#define TAIL_IE_BATTERY_VOLTAGE             0x40
#define TAIL_IE_UPTIME_BLINKS               0x80
#define TAIL_IE_DEBUG                       0xff

#define TAIL_CONFIG_WRITE_SUCCESS			0x00
#define TAIL_CONFIG_WRITE_ERROR_FULL		0x01
#define TAIL_CONFIG_WRITE_ERROR_UNKNOWN		0x02


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
void tail_finish_ranging(void);
void proto_rxtimer(void);


radio_callbacks proto_callbacks = {
		.txdone = proto_txdone,
		.rxdone = proto_rxdone,
		.rxtimeout = proto_rxtimeout,
		.rxerror = proto_rxerror
};

#define BATTERY_FILTER 4
#define BATTERY_BLINKS_VALID 10

void proto_update_battery(void)
{
    uint16_t volts = battery_read();
    if (device.adc_volts == 0)
    	device.adc_volts = volts << BATTERY_FILTER;
    else {
    	device.adc_volts = device.adc_volts - (device.adc_volts >> BATTERY_FILTER) + volts;
    }
    device.adc_validity_counter = BATTERY_BLINKS_VALID + 1;
}

void proto_battery_blink(void)
{
    if (device.adc_validity_counter)
        device.adc_validity_counter--;
}

uint16_t proto_battery_volts(void)
{
    if (device.adc_validity_counter)
        return device.adc_volts >> BATTERY_FILTER;
    else
        return 0;
}

bool proto_battery_flat(void)
{
    return battery_flat(proto_battery_volts());
}

void proto_init(void)
{
	bool configured = false;
    device.eui = 0;
    if (config_get(config_key_eui, (uint8_t *)&device.eui, sizeof(device.eui))) {
    	configured = true;
    }
    lfsr_seed((device.eui & 0xffffffff) ^ (device.eui >> 32));

    device.associated = (config_get8(config_key_associated) != 0);
    device.short_addr = config_get16(config_key_short_addr);
    device.pan = 0;
    if (config_get(config_key_pan, (uint8_t *)&device.pan, sizeof(device.pan)) <= 0)
    	device.pan = PAN_UNASSOCIATED;

    device.radio_active = false;
    device.radio_sleeping = false;

    radio_read_adc_cal(&device.radio_volts_cal, &device.radio_temp_cal);

    battery_init(config_get8(config_key_allow_flat_battery));
    proto_update_battery();

    time_early_wakeup(proto_prepare, PROTO_PREPARETIME);

    timer_init();
    timer_sethandler(proto_rxtimer);

    if (configured)
        tag();
}

void proto_init_window(void)
{
    uint32_t frequency = timer_frequency();

    device.rxnumerator = frequency;
    device.rxdenominator = (uint64_t)DWCLOCK*128;
}

void proto_update_window(void)
{
    uint64_t dwduration = DWTIME_SUB(device.rxendtime, device.rxstarttime);

    device.rxnumerator = device.rxtimer;
    device.rxdenominator = dwduration;
}

void proto_set_timer(uint64_t endtime)
{
    uint8_t now[5];
    /* We can take a slightly more accurate reading by starting the
     * timer running now and updating the timeout once we've done the
     * maths.
     */
    timer_set(0xffff);
    timer_start();
    radio_gettime(now);
    device.rxstarttime = TIMESTAMP_READ(now);
    uint64_t duration = DWTIME_SUB(endtime, device.rxstarttime);
    device.rxtimer = duration * device.rxnumerator / device.rxdenominator;
    timer_set(device.rxtimer);
}

void start_rx(bool delayed)
{
	uint64_t rxendtime;
	uint64_t rxtime;

	device.radio_active = true;
	radio_autoreceive(true);
    radio_setrxtimeout(0); // device.rxtimeout

    if (delayed) {
        uint64_t txtime = tag_data.last_stamp;
        rxtime = DWTIME_ADD(txtime, (uint64_t)device.rxdelay << 16);
        rxtime = RADIO_ALIGN(rxtime);
    } else {
        uint8_t now[5];
        radio_gettime(now);
        rxtime = TIMESTAMP_READ(now);
    }
    rxendtime = DWTIME_ADD(rxtime, (uint64_t)device.rxtimeout << 16);

    proto_set_timer(rxendtime);
    if (delayed)
        radio_setstarttime(rxtime >> 8);
    radio_rxstart(delayed);
}

void proto_txdone(void)
{
	debug.in_txdone = true;
	GPIO_PinOutToggle(gpioPortA, 1);

	uint8_t txtime[5];
	radio_readtxtimestamp(txtime);
	uint32_t timestamp = (uint32_t) (TIMESTAMP_READ(txtime) >> 9);
	tag_data.last_stamp = timestamp;
	entropy_register(timestamp - device.radio_starttime);

	if (device.txtime_ptr) {
		*device.txtime_ptr = timestamp;
		device.txtime_ptr = NULL;
	}

	if (tag_data.ranging_aborted)
		device.radio_active = false;
	else {
		if (device.receive_after_transmit && (tag_data.responses_sent == 0))
			start_rx(true);
		else
			tail_finish_ranging(); /* clears radio_active if done */
	}

	GPIO_PinOutToggle(gpioPortA, 1);
	debug.in_txdone = false;
}

void proto_rxdone(void)
{
	int len;
	uint8_t time[5];

    debug.in_rxdone = true;
	GPIO_PinOutToggle(gpioPortA, 1); // up

	radio_readrxtimestamp(time);
	tag_data.last_stamp = TIMESTAMP_READ(time);

	len = radio_getpayload(rxbuf, BUFLEN);

	if (radio_overflow())
		device.radio_active = false;
	else
        (void) proto_despatch(rxbuf, len);

	GPIO_PinOutToggle(gpioPortA, 1); // down
    debug.in_rxdone = false;
}

void proto_rxtimeout(void)
{
	uint8_t time[5];

	debug.in_rxtimeout = true;
	radio_gettime(time);
	tag_data.last_stamp = TIMESTAMP_READ(time);
	tail_finish_ranging(); /* clears radio_active if done */
	debug.in_rxtimeout = false;
}

void proto_rxtimer(void)
{
	uint8_t time[5];

	radio_txrxoff();

	radio_gettime(time);
	tag_data.last_stamp = TIMESTAMP_READ(time);
	device.rxendtime = TIMESTAMP_READ(time);
	tail_finish_ranging(); /* clears radio_active if done */
	proto_update_window();
}

void proto_rxerror(void)
{
	debug.in_rxerror = true;
   	start_rx(false);
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

/* same units as proto_rx_timeout() */
void proto_rx_delay(uint32_t time)
{
    device.rxdelay = time;
}

/* All values are in ticks */
int32_t add_jitter(int period, int32_t jitter) {
    /* Make jitter an even number to stay centered around period */
    if (jitter & 1)
        jitter -= 1;

    if (jitter <= 0)
        return period;

    period += (lfsr() % (jitter+1)) - (jitter / 2);
    return (period < 0) ? 0 : period;
}

void tag_set_event(uint32_t now)
{
	int32_t period;

	if (!tag_data.idle) {
	    int target_time = time_sub(now, tag_data.transition_time);
        if (time_ge(target_time, accel_last_activity()))
            tag_data.idle = true;
	}

	if (tag_data.idle) {
	    period = add_jitter(tag_data.period_idle, tag_data.jitter_idle);
	} else {
	    period = add_jitter(tag_data.period_active, tag_data.jitter_active);
	}

	if (proto_battery_flat()) {
		event_log(EVENT_BATTERY_FLAT);
		if (period < PERIOD_BATTERY_FLAT)
			period = PERIOD_BATTERY_FLAT;
	}

    uint32_t time = time_add(tag_data.last_event, period);
    if (time_ge(now, time))
        time = now;
    time_event_at(tag_start, time);
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

void tag_start(void)
{
    int offset, ftoffset, iecount, iecountoffset;
    uint8_t voltage, temperature;
    uint8_t now[5];

    tag_data.last_event = time_now();
    tag_set_event(tag_data.last_event);

    if (device.radio_sleeping) {
        event_log(EVENT_RADIO_SLEEPING);
        return;
    }

    if (device.radio_active && !device.just_woken) {
        event_log(EVENT_ALREADY_ACTIVE);
        return;
    }

    device.just_woken = false;
    tag_data.active = true;

    radio_gettime(now);
    /* The bottom 9 bits are constant, so are useless as an entropy source.
       Once discarded, the result is 31 bit. */
    device.radio_starttime = (uint32_t) (TIMESTAMP_READ(now) >> 9);

    if (proto_battery_flat())
    	return;

    device.receive_after_transmit = (tag_data.max_anchors > 0);
    if (tag_data.listen_period != 0) {
        uint32_t next_listen = time_add(tag_data.last_receive_window, tag_data.listen_period);
        if (time_ge(tag_data.last_event, next_listen))
            device.receive_after_transmit = true;
    }

    if (device.receive_after_transmit)
        tag_data.last_receive_window = tag_data.last_event;

    proto_header(txbuf);
    offset = proto_dest(txbuf, &tag_data.target_mac_addr);
    offset = proto_source(txbuf, offset);
    txbuf[offset++] = TAIL_MAGIC;

    int frame_type = TAIL_FRAME_BLINK;
    int flags = 0;

    if (device.receive_after_transmit)
    	flags |= TAIL_FLAGS_LISTEN;

    if (!tag_data.idle)
    	flags |= TAIL_FLAGS_ACCEL;

    /* payload goes here */
    ftoffset = offset;
    txbuf[offset++] = frame_type;
    txbuf[offset++] = flags;

    radio_wakeup_adc_readings(&voltage, &temperature);

    proto_battery_blink();
    uint16_t volts = proto_battery_volts();

    iecountoffset = offset;
    txbuf[offset++] = 0;
    iecount = 0;

    int battery = battery_state(volts);
    if (battery >= 0) {
        txbuf[offset++] = TAIL_IE_BATTERY;
        txbuf[offset++] = battery_state(volts);
        iecount++;
    }

    if (tag_data.tx_battery_voltage) {
        txbuf[offset++] = TAIL_IE_BATTERY_VOLTAGE;
        txbuf[offset++] = volts & 0xff;
        txbuf[offset++] = volts >> 8;
        iecount++;
    }
    if (tag_data.tx_radio_voltage) {
        txbuf[offset++] = TAIL_IE_RADIO_VOLTAGE;
        txbuf[offset++] = device.radio_volts - device.radio_volts_cal;
        iecount++;
    }
    if (tag_data.tx_temperature) {
        txbuf[offset++] = TAIL_IE_TEMPERATURE;
        txbuf[offset++] = temperature - device.radio_temp_cal;
        iecount++;
    }
    if (tag_data.tx_uptime_blinks) {
        txbuf[offset++] = TAIL_IE_UPTIME_BLINKS;
        txbuf[offset++] = device.uptime_blinks & 0xff;
        txbuf[offset++] = (device.uptime_blinks >> 8) & 0xff;
        txbuf[offset++] = (device.uptime_blinks >> 16) & 0xff;
        txbuf[offset++] = device.uptime_blinks >> 24;
        iecount++;
    }

    device.uptime_blinks++;

#if 0
    /* We're now making most of this available through other
     * IEs, so there's not much point in also sending it here.
     */
    txbuf[offset++] = TAIL_IE_DEBUG;
    txbuf[offset++] = 6; /* Length of debug field */
    txbuf[offset++] = voltage; /* Battery state */
    txbuf[offset++] = temperature; /* Temperature */
    txbuf[offset++] = device.radio_volts_cal;
    txbuf[offset++] = device.radio_temp_cal;
    txbuf[offset++] = volts & 0xff;
    txbuf[offset++] = volts >> 8;
    iecount++;
#endif

    if (iecount > 0)
    	txbuf[ftoffset] = frame_type | TAIL_FRAME_BLINK_IE;

    txbuf[iecountoffset] = iecount;

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, false);

    device.txtime_ptr = &tag_data.tx_stamp;
    tag_data.anchors_heard = 0;
    tag_data.responses_sent = 0;
    tag_data.ranging_aborted = false;
	device.radio_active = true;

	radio_txstart(false);
}

void tag_with_period(int period, int period_idle, int transition_time)
{
	proto_prepare();

	radio_setcallbacks(&proto_callbacks);

	tag_data.target_mac_addr = default_target_addr;
    /* Do we want to be able to direct this packet differently at the MAC layer? */

	tag_data.max_anchors = config_get8(config_key_tag_max_anchors);
	if (tag_data.max_anchors > MAX_ANCHORS)
		tag_data.max_anchors = MAX_ANCHORS;

	tag_data.min_responses = config_get8(config_key_tag_min_responses);

	tag_data.period_active = period;
	tag_data.period_idle = period_idle;
	tag_data.transition_time = transition_time;

    uint32_t listen_period = 0;
    config_get(config_key_tag_listen_period, (uint8_t *)&listen_period, sizeof(uint32_t));
    tag_data.listen_period = TIME_FROM_SECONDS((uint64_t)listen_period);
    tag_data.last_receive_window = time_now();

	tag_data.tx_battery_voltage = config_get8(config_key_tx_battery_voltage);
	tag_data.tx_radio_voltage = config_get8(config_key_tx_radio_voltage);
	tag_data.tx_temperature = config_get8(config_key_tx_temperature);
	tag_data.tx_uptime_blinks = config_get8(config_key_tx_uptime_blinks);

	tag_data.jitter_active = TIME_FROM_MS(config_get32(config_key_tag_jitter));
	tag_data.jitter_idle = TIME_FROM_MS(config_get32(config_key_tag_jitter_idle));

	device.receive_after_transmit = (tag_data.max_anchors > 0);

    proto_init_window();

	tag_start();
}

void tag(void)
{
	uint32_t period_active = 0;
	uint32_t period_idle = 0;
	uint32_t transition_time = 0;
	if (config_get(config_key_tag_period, (uint8_t *)&period_active, sizeof(int)) <= 0)
		period_active = PERIOD_DEFAULT_ACTIVE; // 1000;
	if (config_get(config_key_tag_period_idle, (uint8_t *)&period_idle, sizeof(int)) <= 0)
		period_idle = PERIOD_DEFAULT_IDLE; // 100000;
	if (config_get(config_key_tag_transition_time, (uint8_t *)&transition_time, sizeof(int)) <= 0)
		transition_time = 10;
	tag_with_period(TIME_FROM_MS((uint64_t)period_active), TIME_FROM_MS((uint64_t)period_idle), TIME_FROM_SECONDS((uint64_t)transition_time));
}

void stop(void)
{
    radio_callbacks callbacks = { NULL, NULL, NULL, NULL };
    radio_setcallbacks(&callbacks);
	time_event_clear(tag_start);
    timer_stop();
	radio_txrxoff();
    device.radio_active = false;
    tag_data.active = false;
}

bool tail_config(packet_t *p);

void proto_poll()
{
    if (accel_interrupt_fired()) {
#if 0
    	write_string("Movement\r\n");
#endif
        if (tag_data.active) {
            tag_data.idle = false;
            tag_set_event(time_now());
        }
    }
    if (!device.radio_active && !device.radio_sleeping) {
    	if (time_to_next_event() >= PROTO_PREPARETIME) {
    	    device.radio_sleeping = true;
    	    radio_configsleep(RADIO_SLEEP_CONFIG | RADIO_SLEEP_TANDV, RADIO_SLEEP_WAKE_WAKEUP | RADIO_SLEEP_ENABLE);
    	    radio_entersleep();
    	}
    }
    if (!device.radio_active && device.reset_requested)
    	NVIC_SystemReset();
}

/* Called when the radio may be asleep and we need to get ready for action */
void proto_prepare(void)
{
    if (!device.radio_sleeping)
    	return;
    proto_update_battery();
    if (proto_battery_flat())
    	return;
    device.radio_sleeping = false;
    /* Keep the radio awake until it is used */
    device.radio_active = true;
    device.just_woken = true;
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
    proto_update_battery();
    if (proto_battery_flat())
    	return;
    device.radio_sleeping = false;
    radio_wakeup();
    radio_wakeup_adc_readings(&device.radio_volts, &device.radio_temp);
}

int proto_volts(void)
{
	int v = device.radio_volts;
	return 1000 * (v - device.radio_volts_cal) / 173 + 3300;
}

int proto_rawvolts(void)
{
    return device.radio_volts;
}

int proto_temp(void)
{
	int t = device.radio_temp;
	return 1000000 * (t - device.radio_temp_cal) / 1140 + 23000;
}

int proto_rawtemp(void)
{
    return device.radio_temp;
}

uint32_t proto_uptime_blinks(void)
{
    return device.uptime_blinks;
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

void tail_finish_ranging(void)
{
	bool packet_pending = false;
	int offset;

	if (tag_data.responses_sent < tag_data.min_responses)
		packet_pending = true;

	if ((tag_data.anchors_heard > 0) && (tag_data.responses_sent == 0))
		packet_pending = true;

	if (!packet_pending) {
		device.radio_active = false;
		return;
	}

	uint64_t ttx = tag_data.last_stamp + device.turnaround_delay;
    ttx = RADIO_ALIGN(ttx);

	uint64_t td_tx = ttx - tag_data.tx_stamp + device.antenna_delay_tx;

	proto_header(txbuf);
	offset = proto_dest(txbuf, &tag_data.target_mac_addr);
    offset = proto_source(txbuf, offset);
    int frame_type = TAIL_FRAME_RANGING_RESPONSE;
    if (tag_data.max_anchors == 0)
    	frame_type |= TAIL_FRAME_RANGING_RESPONSE_OWR;
    txbuf[offset++] = TAIL_MAGIC;
    txbuf[offset++] = frame_type;

    TIMESTAMP_WRITE(txbuf+offset, td_tx);
    offset += 5;

    if (tag_data.max_anchors != 0) {
        txbuf[offset++] = tag_data.anchors_heard;

        if (tag_data.anchors_heard > 0) {
        	int lbyte = 0;
        	for (int i = 0; i < tag_data.anchors_heard; i++)
        		if (tag_data.anchors[i].address.type == ADDR_LONG)
        			lbyte |= (1<<i);
        	txbuf[offset++] = lbyte;
        }

        for (int i = 0; i < tag_data.anchors_heard; i++) {
        	uint64_t td = tag_data.anchors[i].rx_stamp - tag_data.tx_stamp;

        	switch (tag_data.anchors[i].address.type) {
        	case ADDR_SHORT:
        		WRITE16(txbuf, offset, tag_data.anchors[i].address.a.s);
        		offset += 2;
        		break;
        	case ADDR_LONG:
        	    WRITE64(txbuf, offset, tag_data.anchors[i].address.a.l);
        	    offset += 8;
        	    break;
        	default:
        		/* We have no way to specify no address. Just make one up. */
        		txbuf[offset++] = ADDR_SHORT_BROADCAST & 0xff;
    		    txbuf[offset++] = ADDR_SHORT_BROADCAST >> 8;
    	    	break;
    	    }

    	    TIMESTAMP_WRITE(txbuf+offset, td);
    	    offset += 5;
        }
    }

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, true);
    radio_setstarttime(ttx >> 8);
    radio_txstart(true);

	tag_data.responses_sent++;
}

bool tail_timing(packet_t *p)
{
    if (tag_data.anchors_heard < tag_data.max_anchors) {
		tag_data.anchors[tag_data.anchors_heard].address = p->source;
		tag_data.anchors[tag_data.anchors_heard].rx_stamp = p->timestamp;
		tag_data.anchors_heard++;
	}

	if (tag_data.anchors_heard >= tag_data.max_anchors) {
		radio_txrxoff();
		timer_stop();
		tail_finish_ranging();
		return true;
	}

    return false;
}

#define CHECK_PADDING(p, roffset) do { \
	    int i = (roffset); \
	    while (i < (p)->len) \
	    	if ((p)->payload[i++] != 0) \
	    		return false; \
    } while (0)

/* We need to check if the encrypted data, rounded up to 16 bytes,
 * plus the MAC, plus any unencrypted data, fits within the buffer
 */

#define ROUND16(n) (((n) + 15) & ~0xf)

#define FITS_IN_BUFFER(encryption_start, offset, n) \
	((ROUND16((offset) - (encryption_start) + (n)) + 16 + encryption_start) <= BUFLEN)

bool tail_config(packet_t *p)
{
    /* We're not going to process any more incoming packets after
     * receiving a config request, until the next blink.
     */
    radio_txrxoff();
    timer_stop();
    tag_data.ranging_aborted = true;

    int roffset = p->hlen;
    int subtype = p->payload[roffset++] & 0x0f;
    int count;

	int offset = proto_reply(txbuf, p);
    txbuf[offset++] = TAIL_MAGIC_ENCRYPTED;
    int encryption_start = offset;
    int len = p->len - 2; /* Length of payload after frame header */
    /* Note that we don't necessarily know the exact length, because it
     * will be rounded up to a crypto block size. It should however be
     * padded with zeros.
     */

    switch (subtype) {
    case TAIL_FRAME_CONFIG_RESET:
    	if (len < 2)
    		return false;
    	int magic = READ16(p->payload, roffset);
    	roffset += 2;
    	if (magic != TAIL_MAGIC_RESET_REQUEST)
    		return false;
    	CHECK_PADDING(p, roffset);
    	device.reset_requested = true;
    	txbuf[offset++] = TAIL_FRAME_CONFIG_RESPONSE | TAIL_FRAME_CONFIG_RESET;
        WRITE16(txbuf, offset, TAIL_MAGIC_RESET_RESPONSE);
        offset += 2;
        break;
    case TAIL_FRAME_CONFIG_ENUMERATE:
    	if (len < 2)
    		return false;
    	config_iterator iterator = READ16(p->payload, roffset);
    	roffset += 2;
    	CHECK_PADDING(p, roffset);
    	txbuf[offset++] = TAIL_FRAME_CONFIG_RESPONSE | TAIL_FRAME_CONFIG_ENUMERATE;
    	int values = 0;
    	int iterator_offset = offset;
    	offset += 2;
    	int values_offset = offset;
    	offset++;
    	if (iterator == 0)
    		config_enumerate_start(&iterator);
		else
			if (!config_enumerate_valid(&iterator))
				return false;
		while (FITS_IN_BUFFER(encryption_start, offset, 2)) {
			config_key key = config_enumerate(&iterator);
			if (key == CONFIG_KEY_INVALID) {
				iterator = 0;
				break;
			} else {
				WRITE16(txbuf, offset, key);
				offset += 2;
				values++;
			}
		}
        txbuf[iterator_offset] = iterator;
        txbuf[values_offset] = values;
        break;
    case TAIL_FRAME_CONFIG_READ:
    	if (len < 1)
    		return false;
        count = p->payload[roffset++];
        if (len < 1 + 2*count)
        	return false;
    	CHECK_PADDING(p, roffset+2*count);
    	txbuf[offset++] = TAIL_FRAME_CONFIG_RESPONSE | TAIL_FRAME_CONFIG_READ;
    	int keys_written = 0;
    	int keys_offset = offset++;
    	for (int i = 0; i < count; i++) {
    		config_key key = READ16(p->payload, roffset);
    		roffset += 2;
    		WRITE16(txbuf, offset, key);
    		int keylen = config_get(key, txbuf + offset + 3, BUFLEN-offset-1);
    		if (keylen < 0)
    			continue;
        	offset += 2;
        	txbuf[offset++] = keylen;
        	if (!FITS_IN_BUFFER(encryption_start, offset, keylen)) {
        		offset -= 3;
        		break;
        	}
        	offset += keylen;
        	keys_written++;
    	}
    	txbuf[keys_offset] = keys_written;
        break;
    case TAIL_FRAME_CONFIG_WRITE:
    	if (len < 1)
    		return false;
    	count = p->payload[roffset++];
    	int delta = 0;
    	int roffset_start = roffset;
        for (int i = 0; i < count; i++) {
        	config_key key = READ16(p->payload, roffset);
        	roffset += 2;
        	int keylen = p->payload[roffset++];
        	roffset += keylen;
        	if (p->len < roffset)
        		return false;
        	delta += config_space_required_for_key(keylen);
        	delta -= config_space_used_by_key(key);
        }
        CHECK_PADDING(p, roffset);
        roffset = roffset_start;
        txbuf[offset++] = TAIL_FRAME_CONFIG_RESPONSE | TAIL_FRAME_CONFIG_WRITE;
        int result = TAIL_CONFIG_WRITE_SUCCESS;
        if (delta <= config_freespace()) {
        	/* In order to guarantee that we have the free space available
        	 * regardless of the order in which we write the keys, we need
        	 * to do a deletion pass first. Don't delete keys which are
        	 * already in place, in order to avoid unnecessary wear on the flash.
        	 */
            for (int i = 0; i < count; i++) {
            	config_key key = READ16(p->payload, roffset);
            	roffset += 2;
            	int keylen = p->payload[roffset++];
            	if (!config_key_in_place(key, p->payload+roffset, keylen))
            	    config_delete(key);
            	roffset += keylen;
            }
            roffset = roffset_start;
            /* And now we can finally start writing the new keys. */
            for (int i = 0; i < count; i++) {
            	config_key key = READ16(p->payload, roffset);
            	roffset += 2;
            	int keylen = p->payload[roffset++];
            	/* config_put requires the data to be aligned. We know that we have
            	 * at least 3 bytes available immediately before the data, so we can
            	 * use this to destructively align the data prior to calling
            	 * config_put().
            	 */
            	uint8_t *ptr = (uint8_t *)(((uintptr_t)(p->payload + roffset)) & ~3);
            	if (ptr != p->payload + roffset)
            	    memmove(ptr, p->payload + roffset, keylen);
            	if (!config_put(key, ptr, keylen)) {
            		result = TAIL_CONFIG_WRITE_ERROR_UNKNOWN;
            	    break;
            	}
            	roffset += keylen;
            }
        } else {
        	result = TAIL_CONFIG_WRITE_ERROR_FULL;
        }
        txbuf[offset++] = result;
        break;
    case TAIL_FRAME_CONFIG_DELETE:
    	if (len < 1)
    		return false;
        count = p->payload[roffset++];
        if (len < 1 + 2*count)
        	return false;
    	CHECK_PADDING(p, roffset+2*count);
    	txbuf[offset++] = TAIL_FRAME_CONFIG_RESPONSE | TAIL_FRAME_CONFIG_DELETE;
    	for (int i = 0; i < count; i++) {
    		config_key key = READ16(p->payload, roffset);
    		roffset += 2;
    		config_delete(key);
    	}
    	txbuf[offset++] = TAIL_CONFIG_WRITE_SUCCESS;
        break;
    case TAIL_FRAME_CONFIG_SALT:
    case TAIL_FRAME_CONFIG_TEST:
    default:
    	return false;
    }

    // offset = crypto_encrypt(txbuf + encryption_start, offset - encryption_start) + encryption_start;

    radio_writepayload(txbuf, offset, 0);
    radio_txprepare(offset+2, 0, true);
    radio_txstart(false);

    return true;
}

bool tag_rx(packet_t *p)
{
	bool encrypted = false;
    if ((p->payload[0] != TAIL_MAGIC) && (p->payload[0] != TAIL_MAGIC_ENCRYPTED))
    	return false;
    if (p->payload[0] == TAIL_MAGIC_ENCRYPTED)
    	encrypted = true;
    p->hlen = 1;

#if 0
    if (encrypted)
    	crypto_decrypt(...);
#else
    if (encrypted)
        return false;
#endif

	/* Decode tail packet and despatch */
	int frame_type = p->payload[p->hlen];

	switch (frame_type & 0xf0) {
	case TAIL_FRAME_RANGING_REQUEST:
		return tail_timing(p);
	case TAIL_FRAME_CONFIG_REQUEST:
		if (!encrypted)
			break;
		tail_config(p);
		return false;
	default:
		break;
	}

	return false;
}

/* Return true if a packet transmitted */
bool proto_despatch(uint8_t *buf, int len)
{
	int pp;

    struct packet p;

#if 0
    volatile bool foo = true;
    while (foo) ;
#endif

	if (len < 3)
		/* Invalid packet */
		return false;

	p.timestamp = tag_data.last_stamp;

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

	/* For some reason, gcc seems to have stopped being able to tell that
	 * we only access p.dest.pan in the same conditions as when it's been
	 * initialised. This is an unpleasant workaround.
	 */
	p.dest.pan = PAN_BROADCAST;

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
		case TAIL_MAGIC_ENCRYPTED:
			return tag_rx(&p);
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
