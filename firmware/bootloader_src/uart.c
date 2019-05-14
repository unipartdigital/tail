#include "em_cmu.h"
#include "em_leuart.h"
#include "em_gpio.h"

#include "emlib_wrap.h"
#include "uart.h"
#include "buf.h"

#define RXBUFSIZE 128
#define TXBUFSIZE 128

uint8_t rxbufdata[RXBUFSIZE];
uint8_t txbufdata[TXBUFSIZE];

static buffer rxbuf;
static buffer txbuf;

volatile bool tx_active;

void write_string(const char *s)
{
	uint8_t c;
	while ((c = *s++) != '\0')
	    while (!uart_tx(c))
	    	;
}

// Should be enough, right?
#define S_LEN 22

void write_int(uint32_t n)
{
	char s[S_LEN+1];
	int i;
	bool negative;

	s[S_LEN] = '\0';
	s[S_LEN-1] = '0';
	negative = (n >= (1<<31));
	if (negative) {
		n = ~n;
	    n++;
	}
	for (i = S_LEN-1; n; i--) {
		s[i] = '0' + (n % 10);
		n = n / 10;
	}
	if (i == S_LEN-1)
		i--;
	if (negative)
		s[i--] = '-';

    write_string(s+i+1);
}

void write_hex(uint32_t n)
{
	char s[S_LEN+1];
	int i;

	s[S_LEN] = '\0';
	s[S_LEN-1] = '0';
	for (i = S_LEN-1; n; i--) {
		int digit = (n % 16);
		s[i] = (digit<10) ? ('0' + digit) : ('A' + digit - 10);
		n = n / 16;
	}
	if (i == S_LEN-1)
		i--;

    write_string(s+i+1);
}

void write_int64(uint64_t n)
{
	char s[S_LEN+1];
	int i;
	bool negative;

	s[S_LEN] = '\0';
	s[S_LEN-1] = '0';
	negative = (n >= (1<<31));
	if (negative) {
		n = ~n;
	    n++;
	}
	for (i = S_LEN-1; n; i--) {
		s[i] = '0' + (n % 10);
		n = n / 10;
	}
	if (i == S_LEN-1)
		i--;
	if (negative)
		s[i--] = '-';

    write_string(s+i+1);
}


void LEUART0_IRQHandler(void)
{
	uint8_t data;

	unsigned int flags = LEUART_IntGet(LEUART0);
	LEUART_IntClear(LEUART0, flags);

	while (LEUART_StatusGet(LEUART0) & LEUART_STATUS_RXDATAV) {
		(void) buf_put(&rxbuf, LEUART_RxDataGet(LEUART0));
	}

    while (LEUART_StatusGet(LEUART0) & LEUART_STATUS_TXBL) {
    	if (buf_get(&txbuf, &data)) {
            LEUART_Tx(LEUART0, data);
    	} else {
        	LEUART_IntDisable(LEUART0, LEUART_IEN_TXBL);
    		tx_active = false;
    		return;
    	}
    }
}

void uart_init(void)
{
	buf_init(&rxbuf, rxbufdata, RXBUFSIZE);
	buf_init(&txbuf, txbufdata, TXBUFSIZE);
	tx_active = false;

	// CMU_ClockSelectSet() implicitly enables the correct oscillator
#if 1
	CMU_ClockSelectSet(cmuClock_LFB, cmuSelect_LFXO);
#else
	CMU_ClockSelectSet(cmuClock_LFB, cmuSelect_LFRCO);
#endif

	CMU_ClockEnable(cmuClock_LEUART0, true);
//	CMU_ClockDivSet(cmuClock_LEUART0,cmuClkDiv_1);
//	CMU_ClockSelectSet(cmuClock_LFB, cmuSelect_CORELEDIV2);
//	CMU_ClockDivSet(cmuClock_LEUART0, cmuClockDiv_1); // XXX
	CMU_ClockEnable(cmuClock_CORELE, true);
	GPIO_PinModeSet(gpioPortD, 4, gpioModePushPull, 1);
	GPIO_PinModeSet(gpioPortD, 5, gpioModeInput, 0);
	LEUART_Init_TypeDef leuart_init = LEUART_INIT_DEFAULT;
	LEUART_Init(LEUART0, &leuart_init);
	LEUART0->ROUTE = LEUART_ROUTE_RXPEN | LEUART_ROUTE_TXPEN;

	NVIC_ClearPendingIRQ(LEUART0_IRQn);
    NVIC_EnableIRQ(LEUART0_IRQn);

    LEUART_IntEnable(LEUART0, LEUART_IEN_RXDATAV);
}

void uart_start_tx(void)
{
	tx_active = true;
}

bool uart_tx(uint8_t data)
{
    if (tx_active) {
        return buf_put(&txbuf, data);
    } else {
	    tx_active = true;
    	LEUART_IntEnable(LEUART0, LEUART_IEN_TXBL);
    	LEUART_Tx(LEUART0, data);
    	/* If there's still space in the buffer, we're unlikely to get
    	 * a Tx interrupt.
    	 */
    	if (LEUART_StatusGet(LEUART0) & LEUART_STATUS_TXBL)
    		tx_active = false;
    	return true;
    }
}

bool uart_rx(uint8_t *data)
{
    return buf_get(&rxbuf, data);
}

bool uart_prepare_sleep(void)
{
	return !tx_active;
}
