/* cli.c */

#include <string.h>
#include <stdlib.h>

#include "cli.h"
#include "uart.h"
#include "version.h"
#include "config.h"
#include "flash.h"
#include "time.h"
#include "radio.h"
#include "radio_reg.h"
#include "proto.h"
#include "accel.h"
#include "battery.h"

#include "em_msc.h"

/* 127 bytes for the tx command should fit in this */
#define CLI_MAXLEN 400
#define TX_BUF_SIZE 127
#define TXRX_RXBUFLEN 127

static uint8_t txrx_rxbuf[TXRX_RXBUFLEN];
static int txrx_rxlen;

static char clibuf[CLI_MAXLEN+1];
static int bufp;
static int exep;

#define PROMPT "> "

#define ARRAY_SIZE(x) (sizeof(x) / sizeof(x[0]))

static bool echo;
static void (*cli_pending)(void);

static bool txrx_txcomplete;
static bool txrx_rxcomplete;
static uint8_t txrx_txtime[5];
static uint8_t txrx_rxtime[5];
static bool txrx_rxactive = false;


void cli_init(void)
{
	bufp = 0;
	write_string("Tail cli v" VERSION "\r\nReady for action\r\n" PROMPT);
	echo = true;
	cli_pending = false;
}

#define VALID_CHAR(x) (x > 32)

int find_token(int p)
{
	while ((p < bufp) && !VALID_CHAR(clibuf[p]))
		p++;

	if (p < bufp)
		return p;

	return -1;
}

int token_length(int start)
{
	int p = start;
	while ((p < bufp) && VALID_CHAR(clibuf[p]))
		p++;

	return p - start;
}

bool token_str(char **value)
{
	int p = find_token(exep);
	int l;

	if (p < 0)
		return false;

	l = token_length(p);

	exep = p+l;

	clibuf[p+l] = '\0';
	*value = clibuf+p;

	return true;
}

/* if base == 0, detect base from string */
bool token_int(int *value, int base)
{
	char *ptr;

	if (!token_str(&ptr))
		return false;

	*value = strtol((char *)ptr, NULL, base);

	return true;
}

/* if base == 0, detect base from string */
bool token_uint16(uint16_t *value, int base)
{
	char *ptr;

	if (!token_str(&ptr))
		return false;

	*value = strtoul((char *)ptr, NULL, base);

	return true;
}

/* if base == 0, detect base from string */
bool token_uint32(uint32_t *value, int base)
{
	char *ptr;

	if (!token_str(&ptr))
		return false;

	*value = strtoul((char *)ptr, NULL, base);

	return true;
}

/* if base == 0, detect base from string */
bool token_uint64(uint64_t *value, int base)
{
	char *ptr;

	if (!token_str(&ptr))
		return false;

	*value = strtoull((char *)ptr, NULL, base);

	return true;
}

void fn_read(void)
{
	int addr;
	if (!token_int(&addr, 16)) {
		write_string("Usage: read <address>\r\n");
		return;
	}

    write_hex(*(uint32_t *)addr);
    write_string("\r\n");
}

void fn_write(void)
{
	int addr, value;
	if ((!token_int(&addr, 16)) || (!token_int(&value, 0))) {
		write_string("Usage: write <address> <value>\r\n");
		return;
	}

	flash_write((void *)addr, &value, 4);
}

void fn_erase(void)
{
	int addr;
	if (!token_int(&addr, 16)) {
		write_string("Usage: erase <address>\r\n");
		return;
	}

	flash_erase((void *)addr, FLASH_PAGE_SIZE);
}

void fn_rread(void)
{
	int file;
	int reg;
	int len;
	int i;

	if ((!token_int(&file, 16)) || (!token_int(&reg, 16)) || (!token_int(&len, 0))) {
		write_string("Usage: read <file> <register> <length>\r\n");
		return;
	}

	proto_prepare_immediate();

	/* We're going to use clibuf because at this point it's not going to be reused.
	 * This will be a problem if we ever decide to implement command history.
	 */
	if (len > CLI_MAXLEN+1)
		len = CLI_MAXLEN+1;
	radio_read(file, reg, (uint8_t *)clibuf, len);

	for (i = 0; i < len; i++)
	{
        write_hex(clibuf[i]);
        write_string(" ");
	}
    write_string("\r\n");
}

void fn_rdump(void)
{
	struct { const char *name; uint8_t file; uint16_t reg; uint8_t len; } rset[] = {
#define X(name)			{ #name, RREG(name), RLEN(name) },
			X(DEV_ID)
			X(SYS_STATUS)
			X(SYS_STATE)
			X(SYS_CFG)
			X(SYS_MASK)
			X(SYS_CTRL)
			X(EC_CTRL)
			X(OTP_SF)
			X(OTP_CTRL)
			X(FS_PLLCFG)
			X(FS_PLLTUNE)
			X(FS_XTALT)
			X(RF_RXCTRLH)
			X(RF_TXCTRL)
			X(DRX_TUNE0B)
			X(DRX_TUNE1A)
			X(DRX_TUNE1B)
			X(DRX_TUNE4H)
			X(DRX_TUNE2)
			X(DRX_SFDTOC)
			X(AGC_TUNE2)
			X(AGC_TUNE1)
			X(USR_SFD)
			X(CHAN_CTRL)
			X(TX_FCTRL)
			X(RX_FWTO)
			X(RX_FINFO)
			X(LDE_CFG1)
			X(LDE_CFG2)
			X(LDE_REPC)
			X(DX_TIME)
			X(TX_TIME)
			X(RX_TIME)
			X(PMSC_CTRL0)
			X(PMSC_CTRL1)
			X(PMSC_LEDC)
			X(GPIO_MODE)
			X(AON_WCFG)
			X(AON_CFG0)
			X(AON_CFG1)
			X(AON_CTRL)
			X(LDE_RXANTD)
			X(TX_ANTD)
			X(TX_POWER)
#undef X
	};
	int r, i;

	proto_prepare_immediate();

	for (r = 0; r < ARRAY_SIZE(rset); r++) {
		uint8_t file = rset[r].file;
		uint16_t reg = rset[r].reg;
		int len = rset[r].len;
	    if (len > CLI_MAXLEN+1)
		    len = CLI_MAXLEN+1;
	    radio_read(file, reg, (uint8_t *)clibuf, len);

	    write_string(rset[r].name);
	    write_string(": ");
	    for (i = 0; i < len; i++)
	    {
            write_hex(clibuf[i]);
            write_string(" ");
	    }
        write_string("\r\n");
	}
}

void fn_aread(void)
{
	int reg;
	int len = 1;
	int i;

	if (!token_int(&reg, 16)) {
		write_string("Usage: aread <register> [length]\r\n");
		return;
	}

    token_int(&len, 0);

	for (i = 0; i < len; i++)
	{
		uint8_t value = accel_read(reg);
		reg++;
        write_hex(value);
        write_string(" ");
	}
    write_string("\r\n");
}

void fn_awrite(void)
{
	int reg;
	int value;

	if ((!token_int(&reg, 16)) || (!token_int(&value, 0))) {
		write_string("Usage: awrite <register> <value>\r\n");
		return;
	}

	accel_write(reg, value);
}

void fn_accel(void)
{
	uint16_t x, y, z;
	accel_readings(&x, &y, &z);
	write_int(x);
	write_string(" ");
	write_int(y);
	write_string(" ");
	write_int(z);
	write_string("\r\n");
}

void fn_stop(void)
{
	txrx_rxactive = false;
	stop();
}

void fn_tag(void)
{
	int period = 1000;
	int period_idle = 100000;
	int transition_time = 10;
	(void) token_int(&period, 0);
	(void) token_int(&period_idle, 0);
	(void) token_int(&transition_time, 0);

	tag_with_period(TIME_FROM_MS(period), TIME_FROM_MS(period_idle),
			TIME_FROM_SECONDS(transition_time));
}

void fn_power(void)
{
	uint32_t power;

	if (!token_uint32(&power, 16)) {
		write_string("Usage: power <register value>\r\n");
	    return;
    }

	proto_prepare_immediate();
	radio_settxpower(power);
}

void fn_smartpower(void)
{
	int enabled;

	if (!token_int(&enabled, 0)) {
		write_string("Usage: smartpower <1|0>\r\n");
	    return;
    }

	proto_prepare_immediate();
	radio_smarttxpowercontrol(enabled);
}

void fn_turnaround_delay(void)
{
	uint32_t us;

	if (!token_uint32(&us, 0)) {
		write_string("Usage: turnaround_delay <microseconds>\r\n");
	    return;
    }

	proto_turnaround_delay(us);
}

void fn_rxtimeout(void)
{
	uint32_t time;

	if (!token_uint32(&time, 0)) {
		write_string("Usage: rxtimeout <time>\r\n");
		write_string("time is in units of 1.0256 us (512/499.2MHz)\r\n");
	    return;
    }

	proto_rx_timeout(time);
}

/* We pass in the buffer because this is called from fn_config which has already allocated
 * a large enough buffer. We don't want to allocate it twice on the stack.
 */
void display_key(config_key key, uint8_t *buf, int len)
{
	int l;
	const char *name;
	int namelen;

	if ((l = config_get(key, buf, len)) < 0) {
		write_string("Key not found\r\n");
		return;
	}

	name = config_key_to_name(key);
	namelen = strlen(name);

	write_string(name);
	write_string(": ");

	for (int i = 0; i < l; i++) {
		if (i) {
		    if (i % 16)
		        write_string(" ");
		    else {
			    write_string("\r\n");
		        for (int j = 0; j < namelen+2; j++)
		        	write_string(" ");
		    }
		}
		write_hex(buf[i]);
	}
	write_string("\r\n");
}

void fn_config(void)
{
	config_key key;
	char *name;
	uint8_t buf[CONFIG_KEY_MAXLEN];
	int len;
	int value;
	if (!token_str(&name)) {
		config_iterator iterator;
		config_enumerate_start(&iterator);
		while ((key = config_enumerate(&iterator)) != CONFIG_KEY_INVALID) {
			display_key(key, buf, CONFIG_KEY_MAXLEN);
		}
		return;
	}
	for (len = 0; (len < CONFIG_KEY_MAXLEN) && token_int(&value, 0); len++) {
		if ((value > 0xff) || (value < 0)) {
			write_string("Values must fit within a byte\r\n");
			return;
		}
	    buf[len] = value;
	}

	key = config_key_from_name(name);

	if (key == CONFIG_KEY_INVALID) {
		write_string("Key not known\r\n");
		return;
	}

	if (len == 0) {
		display_key(key, buf, CONFIG_KEY_MAXLEN);
	    return;
	}

	if (!config_put(key, buf, len))
		write_string("Error writing key\r\n");
}

void fn_delete(void)
{
	config_key key;
	char *name;
	if (!token_str(&name)) {
		write_string("Which key do you want to delete?\r\n");
		return;
	}

	key = config_key_from_name(name);

	if (key == CONFIG_KEY_INVALID) {
		write_string("Key not known\r\n");
		return;
	}

	config_delete(key);
}

void fn_free(void)
{
	int free = config_freespace();
	write_int(free);
	write_string("\r\n");
}

void fn_dump(void)
{
	config_dump();
}

void fn_reset(void)
{
	write_string("\r\n");
	NVIC_SystemReset();
}

void fn_echo(void)
{
	int val;
	if (token_int(&val, 0))
		echo = val;
}

void txrx_txdone(void)
{
	radio_readtxtimestamp(txrx_txtime);
	txrx_txcomplete = true;
	if (txrx_rxactive)
		radio_rxstart(false);
}

void txrx_rxdone(void)
{
	if (txrx_rxcomplete) {
		radio_rxstart(false);
		return;
	}

	txrx_rxlen = radio_getpayload(txrx_rxbuf, TXRX_RXBUFLEN) - 2;
	radio_readrxtimestamp(txrx_rxtime);

	txrx_rxcomplete = true;

	radio_rxstart(false);
}

void txrx_recover(void)
{
	radio_rxstart(false);
}

void tx_poll(void)
{
	if (!txrx_txcomplete)
		return;

	txrx_txcomplete = false;
	cli_pending = NULL;
	for (int i = 0; i < 5; i++) {
    	write_hex(txrx_txtime[i]);
    	if (i < 4)
        	write_string(" ");
	}
	write_string("\r\n");
}

void rx_poll(void)
{
	if (!txrx_rxcomplete)
		return;

	write_hex(txrx_rxlen);
	write_string(": ");

	for (int i = 0; i < txrx_rxlen; i++) {
		write_hex(txrx_rxbuf[i]);
		if (i < txrx_rxlen-1)
			write_string(" ");
	}
	write_string("\r\n");
	for (int i = 0; i < 5; i++) {
    	write_hex(txrx_rxtime[i]);
    	if (i < 4)
        	write_string(" ");
	}
	write_string("\r\n");
	txrx_rxcomplete = false;
}

static radio_callbacks txrx_callbacks = {
		.txdone = txrx_txdone,
		.rxdone = txrx_rxdone,
		.rxtimeout = txrx_recover,
		.rxerror = txrx_recover
};

void fn_tx(void)
{
	uint8_t buf[TX_BUF_SIZE];
    int i, val;
    for (i = 0; (i < TX_BUF_SIZE) && token_int(&val, 16); i++)
        buf[i] = val;

    radio_txrxoff();

	radio_setcallbacks(&txrx_callbacks);

    radio_writepayload((uint8_t *)buf, i, 0);
    radio_txprepare(i+2, 0, false);

    cli_pending = tx_poll;

	radio_txstart(false);
}

void fn_rx(void)
{
	int timeout = 0;
	token_int(&timeout, 0);

	txrx_rxactive = true;
	radio_setrxtimeout(timeout);
	radio_setcallbacks(&txrx_callbacks);
	radio_rxstart(false);
}

bool cli_prepare_sleep(void)
{
	return (cli_pending == NULL);
}

void fn_status(void)
{
	proto_prepare_immediate();
	uint32_t status = radio_read32(RREG(SYS_STATUS));
    write_hex(status);
    write_string("\r\n");
}

void fn_battery(void)
{
	uint16_t volts = proto_battery_volts();
	int status = battery_state(volts);
    write_int(status);
    write_string("\r\n");
}

void fn_help_config(void)
{
	write_string("Recognised config variables:\r\n");
	config_key key;
	config_enumerate_key_names_start(&key);
	const char *name;
	while ((name = config_enumerate_key_names(&key)) != NULL) {
		write_string("  ");
		write_string(name);
		write_string("\r\n");
	}
}

void fn_sleep(void)
{
	radio_configsleep(RADIO_SLEEP_CONFIG | RADIO_SLEEP_TANDV, RADIO_SLEEP_WAKE_WAKEUP | RADIO_SLEEP_ENABLE);
	radio_entersleep();
}

void fn_wake(void)
{
	radio_wakeup();
}

void write_int3(int n)
{
	int i = n / 1000;
	int d = n % 1000;
	int z = 0;
	if (d < 100)
		z++;
	if (d < 10)
		z++;
	write_int(i);
	write_string(".");
	while (z--)
		write_string("0");
	write_int(d);
}
void fn_volts(void)
{
	write_int3(proto_volts());
	write_string("\r\n");
}

void fn_temp(void)
{
	write_int3(proto_temp());
	write_string("\r\n");
}

#include "em_gpio.h"

#define SWCLK gpioPortA, 0
#define SWDIO gpioPortA, 1
#define RESET gpioPortA, 2

void send_aap_expansion(void)
{
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
	GPIO_PinOutToggle(SWDIO);
}

uint32_t read_swd(uint32_t address, bool ap)
{
	int bits = 1; /* Read */
	GPIO_PinOutSet(SWDIO); // Start bit
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (ap) {
		GPIO_PinOutSet(SWDIO);
		bits++;
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutSet(SWDIO); // Read
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (address & 0x04) {
		GPIO_PinOutSet(SWDIO);
		bits++;
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (address & 0x08) {
		bits++;
		GPIO_PinOutSet(SWDIO);
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (bits & 1) {
		GPIO_PinOutSet(SWDIO);
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutClear(SWDIO); // Stop
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutSet(SWDIO); // Park
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinModeSet(SWDIO, gpioModeInput, 0);
	GPIO_PinOutSet(SWCLK); 	/* Turnaround */
	GPIO_PinOutClear(SWCLK);

    uint32_t ack = 0;
    uint32_t value = 0;

	for (int i = 0; i < 3; i++) {
		GPIO_PinOutSet(SWCLK);
		ack |= (GPIO_PinInGet(SWDIO) << i);
		GPIO_PinOutClear(SWCLK);
	}

	for (int i = 0; i < 32; i++) {
		GPIO_PinOutSet(SWCLK);
		value |= (GPIO_PinInGet(SWDIO) << i);
		GPIO_PinOutClear(SWCLK);
	}

    GPIO_PinOutSet(SWCLK);
	int parity = GPIO_PinInGet(SWDIO);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinModeSet(SWDIO, gpioModePushPull, 0);
	GPIO_PinOutSet(SWCLK); 	/* Turnaround */
	GPIO_PinOutClear(SWCLK);

	return value;
}

void write_swd(uint32_t address, bool ap, uint32_t value)
{
	int bits = 0; /* Read */
	GPIO_PinOutSet(SWDIO); // Start bit
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (ap) {
		GPIO_PinOutSet(SWDIO);
		bits++;
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutClear(SWDIO); // Write
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (address & 0x04) {
		GPIO_PinOutSet(SWDIO);
		bits++;
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (address & 0x08) {
		bits++;
		GPIO_PinOutSet(SWDIO);
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	if (bits & 1) {
		GPIO_PinOutSet(SWDIO);
	} else
		GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutClear(SWDIO); // Stop
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinOutSet(SWDIO); // Park
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	GPIO_PinModeSet(SWDIO, gpioModeInput, 0);
	GPIO_PinOutSet(SWCLK); 	/* Turnaround */
	GPIO_PinOutClear(SWCLK);

    uint32_t ack = 0;

	for (int i = 0; i < 3; i++) {
		GPIO_PinOutSet(SWCLK);
		ack |= (GPIO_PinInGet(SWDIO) << i);
		GPIO_PinOutClear(SWCLK);
	}

	GPIO_PinModeSet(SWDIO, gpioModePushPull, 0);
	GPIO_PinOutSet(SWCLK); 	/* Turnaround */
	GPIO_PinOutClear(SWCLK);

	bits = 0;

	for (int i = 0; i < 32; i++) {
		if (value & (1<<i)) {
			bits++;
		    GPIO_PinOutSet(SWDIO);
		} else
			GPIO_PinOutClear(SWDIO);
		GPIO_PinOutSet(SWCLK);
		GPIO_PinOutClear(SWCLK);
	}

    if (bits & 1)
	    GPIO_PinOutSet(SWDIO);
    else
	    GPIO_PinOutClear(SWDIO);
    GPIO_PinOutSet(SWCLK);
    GPIO_PinOutClear(SWCLK);
}


void send_line_reset(void)
{
	GPIO_PinOutSet(SWDIO);
	for (int i = 0; i < 50; i++) {
		GPIO_PinOutSet(SWCLK);
		GPIO_PinOutClear(SWCLK);
	}
}

void send_swd_switch(void)
{
	// 0111
	GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	// 1001
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWDIO);
    GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	// 1110
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);

	// 0111
	GPIO_PinOutClear(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWDIO);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
	GPIO_PinOutSet(SWCLK);
	GPIO_PinOutClear(SWCLK);
}

uint32_t read_memory(uint32_t address)
{
    write_swd(0x04, true, address);
    read_swd(0x0c, true);
    return read_swd(0x0c, false);
}

void write_memory(uint32_t address, uint32_t value)
{
    write_swd(0x04, true, address);
    write_swd(0x0c, true, value);
}

void fn_unbrick(void)
{
	GPIO_PinModeSet(RESET, gpioModePushPull, 0);
	GPIO_PinModeSet(SWCLK, gpioModePushPull, 0);
	GPIO_PinModeSet(SWDIO, gpioModePushPull, 0);
    GPIO_PinOutClear(RESET);
    send_aap_expansion();
    GPIO_PinOutSet(RESET);

    for (volatile int d = 0; d < 250; d++)
    	;

    for (int i = 0; i < 1; i++) {
        send_line_reset();
        GPIO_PinOutClear(SWDIO);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);

        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);

        send_swd_switch();
        send_line_reset();

        GPIO_PinOutClear(SWDIO);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);
        GPIO_PinOutSet(SWCLK);
        GPIO_PinOutClear(SWCLK);

        uint32_t idcode = read_swd(0, 0);

        write_swd(0x04, false, 0x50000000); // power up
        write_swd(0x08, false, 0x000000F0); // Access AP0 high bank
        read_swd(0xc, true);
        uint32_t idr = read_swd(0xc, false);
        write_swd(0x08, false, 0x00000000); // Access AP0

        write_swd(0x00, true, 0x00000002); // 32-bit transfers
        uint32_t aapidr = read_memory(0xF0E000FC);
        write_memory(0xF0E00004, 0xcfacc118); // Enable AAP_CMD
        write_memory(0xF0E00000, 0x00000001); // DEVICEERASE
        write_memory(0xF0E00004, 0x00000000); // Disable AAP_CMD and execute

        uint32_t status = read_memory(0xF0E00008);

        write_string("IDCODE: ");
        write_hex(idcode);
        write_string("\r\nIDR: ");
        write_hex(idr);
        write_string("\r\nAAPIDR: ");
        write_hex(aapidr);
        write_string("\r\nStatus: ");
        write_hex(status);
        write_string("\r\n");
    }
}

typedef struct {
	const char *command;
	void (*fn)(void);
} command;

void fn_help(void);

static command command_table[] = {
		{"help", &fn_help},
		{"help_config", &fn_help_config},
		{"read", &fn_read},
		{"write", &fn_write},
		{"erase", &fn_erase},
		{"tag", &fn_tag},
		{"stop", &fn_stop},
		{"config", &fn_config},
		{"delete", &fn_delete},
		{"free", &fn_free},
		{"dump", &fn_dump},
		{"reset", &fn_reset},
		{"echo", &fn_echo},
		{"tx", &fn_tx},
		{"rx", &fn_rx},
		{"status", &fn_status},
		{"sleep", &fn_sleep},
		{"wake", &fn_wake},
		{"rread", &fn_rread},
		{"rdump", &fn_rdump},
		{"aread", &fn_aread},
		{"awrite", &fn_awrite},
		{"volts", &fn_volts},
		{"temp", &fn_temp},
		{"power", &fn_power},
		{"smartpower", &fn_smartpower},
		{"turnaround_delay", &fn_turnaround_delay},
		{"rxtimeout", &fn_rxtimeout},
		{"accel", &fn_accel},
		{"battery", &fn_battery},
		{"unbrick", &fn_unbrick}
};

void fn_help(void)
{
	write_string("Recognised commands:\r\n");
	for (int i = 0; i < ARRAY_SIZE(command_table); i++) {
		write_string("  ");
		write_string(command_table[i].command);
		write_string("\r\n");
	}
}


void cli_execute(void)
{
	int i;
	char *command;

	exep = 0;

	if (!token_str(&command))
		return;

	for (i = 0; i < ARRAY_SIZE(command_table); i++) {
		if (strcmp(command, command_table[i].command) == 0){
			command_table[i].fn();
			return;
		}
	}
	write_string("Unrecognised command\r\n");
}

void cli_poll(void)
{
	uint8_t c;
	if (cli_pending) {
		cli_pending();
		if (cli_pending)
			return;
		write_string(PROMPT);
	}
	if (!cli_pending)
    	rx_poll();
	while (uart_rx(&c)) {
#if 0
		write_int(c);
	    write_string(".");
#endif
		switch (c) {
		case '\0':
			break;
		case 21: // Ctrl-U
           	write_string("\r" PROMPT "\e[K");
           	bufp = 0;
           	break;
		case 3: // Ctrl-C
			write_string("\r\n" PROMPT);
			bufp = 0;
			break;
		case '\b':
			if (bufp > 0) {
			    bufp--;
			    if (echo)
			        uart_tx(c);
			}
			break;
		case '\r':
		case '\n':
			write_string("\r\n");
			cli_execute();
			if (!cli_pending)
    			write_string(PROMPT);
			bufp = 0;
			break;
	    /* Maybe also process delete/backspace here? */
		default:
			if (c < 32)
				break;
			if (bufp >= CLI_MAXLEN)
				break;
		    clibuf[bufp++] = c;
		    if (echo)
		        uart_tx(c);
		}
	}
}
