/* cli.c */

#include <string.h>
#include <stdlib.h>

#include "cli.h"
#include "uart.h"
#include "version.h"
#include "config.h"
#include "flash.h"
#include "battery.h"

#include "em_msc.h"

/* 127 bytes for the tx command should fit in this */
#define CLI_MAXLEN 400

static char clibuf[CLI_MAXLEN+1];
static int bufp;
static int exep;

#define PROMPT "> "

#define ARRAY_SIZE(x) (sizeof(x) / sizeof(x[0]))

static bool echo;
static void (*cli_pending)(void);

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

bool cli_prepare_sleep(void)
{
	return (cli_pending == NULL);
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
		{"config", &fn_config},
		{"delete", &fn_delete},
		{"free", &fn_free},
		{"dump", &fn_dump},
		{"reset", &fn_reset},
		{"echo", &fn_echo},
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