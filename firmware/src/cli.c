/* cli.c */

#include <string.h>
#include <stdlib.h>

#include "aes.h"
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

typedef struct {
	const char *command;
	void (*fn)(void);
} command;

void fn_help(void);

void set8bytes(uint8_t *buf, uint64_t in) {
    int i;
    uint8_t *in_b = (uint8_t *) &in;

    for (i = 0; i < 8; i++) {
        buf[i] = in_b[7 - i];
    }
}

void set16bytes(uint8_t *buf, uint64_t in0, uint64_t in1) {
    set8bytes(buf, in0);
    set8bytes(buf + 8, in1);
}

void show_mem_dbg(uint8_t *base, int n) {
    int i, t;
    for (i = 0; i < n; i++) {
        t = (uint32_t) base[i];
        write_hex(t);
        write_string(" ");
    }
    write_string("\r\n");
}

void check_aes_test(uint8_t *out, uint8_t *expected, int blocks) {
    int eq = memcmp(out, expected, blocks * 16);
    if (eq == 0) {
        write_string("equal, crypto test passed!\r\n");
    } else {
        write_string("not equal, crypto test failed!\r\n");
        show_mem_dbg(out, blocks * 16);
    }
}

void fn_test_aes(void) {
    uint8_t out[16];
    uint8_t in[48];
    uint8_t key[16];
    uint8_t iv[16];
    uint8_t expected[48];

    /* CBCKeySbox128.rsp 20 - check non-zero key*/
    write_string("CBC: 1 block, non-zero key, encrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in, 0, 0);
    set16bytes(key, 0xfebd9a24d8b65c1c, 0x787d50a4ed3619a9);
    set16bytes(iv, 0, 0);

    set16bytes(expected, 0xf4a70d8af877f9b0, 0x2b4c40df57d45b17);
    aes_cbc128(out, in, 16, key, iv, true);
    check_aes_test(out, expected, 1);

    /* CBCKeySbox128.rsp 20 - check in = out */
    write_string("CBC: 1 block, in = out, encrypt: ");
    set16bytes(in, 0, 0);
    set16bytes(key, 0xfebd9a24d8b65c1c, 0x787d50a4ed3619a9);
    set16bytes(iv, 0, 0);

    set16bytes(expected, 0xf4a70d8af877f9b0, 0x2b4c40df57d45b17);
    aes_cbc128(in, in, 16, key, iv, true);
    check_aes_test(in, expected, 1);

    /* CBCVarTxt128.rsp 0 - check non-zero plaintext */
    write_string("CBC: 1 block, non-zero plaintext, encrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in, 0x8000000000000000, 0);
    set16bytes(key, 0, 0);
    set16bytes(iv, 0, 0);

    set16bytes(expected, 0x3ad78e726c1ec02b, 0x7ebfe92b23d9ec34);
    aes_cbc128(out, in, 16, key, iv, true);
    check_aes_test(out, expected, 1);

    /* CBCMMT128.rsp 0 - 1 block */
    write_string("CBC: 1 block, non-zero vals, encrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in,  0x45cf12964fc824ab, 0x76616ae2f4bf0822);
    set16bytes(key, 0x1f8e4973953f3fb0, 0xbd6b16662e9a3c17);
    set16bytes(iv,  0x2fe2b333ceda8f98, 0xf4a99b40d2cd34a8);

    set16bytes(expected, 0x0f61c4d44c5147c0, 0x3c195ad7e2cc12b2);
    aes_cbc128(out, in, 16, key, iv, true);
    check_aes_test(out, expected, 1);

    /* CBCMMT128.rsp 1 - two blocks */
    write_string("CBC: 2 blocks, non-zero vals, encrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in,    0x068b25c7bfb1f8bd, 0xd4cfc908f69dffc5);
    set16bytes(in+16, 0xddc726a197f0e5f7, 0x20f730393279be91);
    set16bytes(key,   0x0700d603a1c514e4, 0x6b6191ba430a3a0c);
    set16bytes(iv,    0xaad1583cd91365e3, 0xbb2f0c3430d065bb);

    set16bytes(expected,   0xc4dc61d9725967a3, 0x020104a9738f2386);
    set16bytes(expected+16, 0x8527ce839aab1752, 0xfd8bdb95a82c4d00);
    aes_cbc128(in, in, 32, key, iv, true);
    check_aes_test(in, expected, 2);

    /* CBCMMT128.rsp 2 - 3 blocks */
    write_string("CBC: 3 blocks, non-zero vals, encrypt: ");
    set16bytes(out,         0,                  0);
    set16bytes(in,          0x9b7cee827a26575a, 0xfdbb7c7a329f8872);
    set16bytes(in+16,       0x38052e3601a79174, 0x56ba61251c214763);
    set16bytes(in+32,       0xd5e1847a6ad5d541, 0x27a399ab07ee3599);
    set16bytes(key,         0x3348aa51e9a45c2d, 0xbe33ccc47f96e8de);
    set16bytes(iv,          0x19153c673160df2b, 0x1d38c28060e59b96);

    set16bytes(expected,    0xd5aed6c9622ec451, 0xa15db12819952b67);
    set16bytes(expected+16,  0x52501cf05cdbf8cd, 0xa34a457726ded978);
    set16bytes(expected+32, 0x18e1f127a28d72db, 0x5652749f0c6afee5);
    aes_cbc128(in, in, 48, key, iv, true);
    check_aes_test(in, expected, 3);

    /* CBCKeySbox128.rsp 20 decrypt */
    write_string("CBC: 1 block, decrypt w/derived key: ");
    set16bytes(out, 0, 0);
    set16bytes(in,  0xf4a70d8af877f9b0, 0x2b4c40df57d45b17);
    set16bytes(key, 0xfebd9a24d8b65c1c, 0x787d50a4ed3619a9);
    set16bytes(iv,  0, 0);

    set16bytes(expected, 0, 0);
    aes_cbc128_encdecrypt(out, in, 16, key, iv);
    check_aes_test(out, expected, 1);

    /* CBCMMT128.rsp 1 - two blocks, decrypt */
    write_string("CBC: 2 block, decrypt w/derived key: ");
    set16bytes(out,   0, 0);
    set16bytes(in,    0x5d6fed86f0c4fe59, 0xa078d6361a142812);
    set16bytes(in+16, 0x514b295dc62ff5d6, 0x08a42ea37614e6a1);
    set16bytes(key,   0x625eefa18a475645, 0x4e218d8bfed56e36);
    set16bytes(iv,    0x73d9d0e27c2ec568, 0xfbc11f6a0998d7c8);

    set16bytes(expected,    0x360dc1896ce601df, 0xb2a949250067aad9);
    set16bytes(expected+16, 0x6737847a4580ede2, 0x654a329b842fe81e);
    aes_cbc128_encdecrypt(out, in, 32, key, iv);
    check_aes_test(out, expected, 2);

    /* CBCMMT128.rsp 0 - 1 block, round trip */
    write_string("CBC: 1 block, round trip encrypt+decrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in,  0x45cf12964fc824ab, 0x76616ae2f4bf0822);
    set16bytes(key, 0x1f8e4973953f3fb0, 0xbd6b16662e9a3c17);
    set16bytes(iv,  0x2fe2b333ceda8f98, 0xf4a99b40d2cd34a8);

    set16bytes(expected, 0x0f61c4d44c5147c0, 0x3c195ad7e2cc12b2);
    aes_cbc128(out, in, 16, key, iv, true);
    check_aes_test(out, expected, 1);

    write_string("... continuing test: ");
    set16bytes(expected,  0x45cf12964fc824ab, 0x76616ae2f4bf0822);
    aes_cbc128_encdecrypt(out, out, 16, key, iv);
    check_aes_test(out, expected, 1);

    /* ECBKeySbox128.rsp 20. Only one block, so ECB = CBC */
    write_string("ECB: 1 block, non-zero key, encrypt: ");
    set16bytes(out, 0, 0);
    set16bytes(in, 0, 0);
    set16bytes(key, 0xfebd9a24d8b65c1c, 0x787d50a4ed3619a9);

    set16bytes(expected, 0xf4a70d8af877f9b0, 0x2b4c40df57d45b17);
    aes_ecb128(out, in, 16, key, true);
    check_aes_test(out, expected, 1);


    /* ECBMMT128.rsp 1 - two blocks */
    write_string("ECB: 2 blocks, non-zero vals, encrypt: ");
    set16bytes(out,   0, 0);
    set16bytes(in,    0x1b0a69b7bc534c16, 0xcecffae02cc53231);
    set16bytes(in+16, 0x90ceb413f1db3e9f, 0x0f79ba654c54b60e);
    set16bytes(key,   0x7723d87d773a8bbf, 0xe1ae5b081235b566);

    set16bytes(expected,    0xad5b089515e78210, 0x87c61652dc477ab1);
    set16bytes(expected+16, 0xf2cc6331a70dfc59, 0xc9ffb0c723c682f6);
    aes_ecb128(in, in, 32, key, true);
    check_aes_test(in, expected, 2);

    /* ECBKeySbox128.rsp 20. Only one block, so ECB = CBC. Decrypt */
    write_string("ECB: 1 block, non-zero key, decrypt2: ");
    set16bytes(out, 0, 0);
    set16bytes(in, 0xf4a70d8af877f9b0, 0x2b4c40df57d45b17);
    set16bytes(key, 0xfebd9a24d8b65c1c, 0x787d50a4ed3619a9);
    set16bytes(expected, 0, 0);

    /* check using the wrapper API that takes encryption keys */
    aes_ecb128_encdecrypt(out, in, 16, key);
    check_aes_test(out, expected, 1);

    /* check in a way that requires turning AES hardware on twice */
    write_string("Same test, different internal API: ");
    aes_decrypt_key128(key, key);
    aes_ecb128(out, in, 16, key, false);
    check_aes_test(out, expected, 1);
}

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
		{"test_aes", &fn_test_aes}
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
