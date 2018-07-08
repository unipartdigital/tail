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

void fn_test(void)
{
	int i;
	if (!token_int(&i, 0)) {
		write_string("Error: expected number\r\n");
		return;
	}

	write_string("Integer: ");
	write_int(i);
	write_string("\r\n");
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

void fn_stop(void)
{
	txrx_rxactive = false;
	stop();
}

void fn_tag(void)
{
	tag();
}

void fn_anchor(void)
{
	anchor();
}

bool range_args(address_t *a, bool average)
{
    a->type = ADDR_NONE;
	if (token_uint16(&a->pan, 16)) {
		char *p;
		if (token_str(&p)) {
	    	if (*p == 's') {
	    		a->type = ADDR_SHORT;
	    		if (!token_uint16(&a->a.s, 16)) {
	    			write_string("16-bit address expected after s\r\n");
	    		    return false;
	    	    }
	    	} else if (*p == 'l') {
	        	a->type = ADDR_LONG;
	    		if (!token_uint64(&a->a.l, 16)) {
	    			write_string("64-bit address expected after l\r\n");
	    		    return false;
	    	    }
	        } else {
	        	write_string("<s/l> must be s or l\r\n");
	        	return false;
	        }
	    }
		if (a->type == ADDR_NONE) {
			if (average)
			    write_string("Usage: raverage <period> <count> [<pan> <s/l> <address>]\r\n");
			else
			    write_string("Usage: range [<pan> <s/l> <address>]\r\n");
			return false;
		}
	}
    return true;
}

void fn_range(void)
{
	address_t a;

	if (range_args(&a, false))
	    range(&a);
}

void fn_raverage(void)
{
	int period = 10;
	int count = 1000;
	address_t a;

	(void) token_int(&period, 0);
	(void) token_int(&count, 0);

	if (range_args(&a, true))
        range_average(&a, TIME_FROM_MS(period), count);
}

void fn_ranchor(void)
{
	ranchor();
}

void fn_tagipv6(void)
{
	int period = 1000;
	(void) token_int(&period, 0);

	tagipv6_with_period(TIME_FROM_MS(period));
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

void fn_reset(void)
{
	write_string("\r\n");
	NVIC_SystemReset();
}

void fn_average(void)
{
	int period = 10;
	int count = 1000;

	(void) token_int(&period, 0);
	(void) token_int(&count, 0);

    tag_average(TIME_FROM_MS(period), count);
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
    uint32_t status = radio_read32(RREG(SYS_STATUS));
    write_hex(status);
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

typedef struct {
	const char *command;
	void (*fn)(void);
} command;

void fn_help(void);

static command command_table[] = {
		{"help", &fn_help},
		{"help_config", &fn_help_config},
		{"test", &fn_test},
		{"read", &fn_read},
		{"write", &fn_write},
		{"erase", &fn_erase},
		{"tag",  &fn_tag},
		{"anchor", &fn_anchor},
		{"stop", &fn_stop},
		{"config", &fn_config},
		{"delete", &fn_delete},
		{"reset", &fn_reset},
		{"average", &fn_average},
		{"echo", &fn_echo},
		{"tx", &fn_tx},
		{"rx", &fn_rx},
		{"range", &fn_range},
		{"ranchor", &fn_ranchor},
		{"raverage", &fn_raverage},
		{"status", &fn_status},
		{"tagipv6", &fn_tagipv6},
		{"sleep", &fn_sleep},
		{"wake", &fn_wake}
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
			if (bufp == 0)
				break;
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
