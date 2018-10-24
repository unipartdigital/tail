#include "em_device.h"
#include "em_chip.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_usart.h"

#include "accel_spi.h"

#define PORT_CS_V1 gpioPortC
#define PIN_CS_V1  14

#define PORT_CLK_V1 gpioPortC
#define PIN_CLK_V1  15

#define PORT_MOSI_V1 gpioPortC
#define PIN_MOSI_V1  0

#define PORT_MISO_V1 gpioPortC
#define PIN_MISO_V1  1


#define PORT_CS_V2 gpioPortC
#define PIN_CS_V2  0

#define PORT_CLK_V2 gpioPortC
#define PIN_CLK_V2  3

#define PORT_MOSI_V2 gpioPortC
#define PIN_MOSI_V2  1

#define PORT_MISO_V2 gpioPortC
#define PIN_MISO_V2  2

/* As the port is the same everywhere... */

#define PORT_CS PORT_CS_V2
#define PORT_CLK PORT_CLK_V2
#define PORT_MOSI PORT_MOSI_V2
#define PORT_MISO PORT_MISO_V2

#define PIN_CS pin_cs
#define PIN_CLK pin_clk
#define PIN_MOSI pin_mosi
#define PIN_MISO pin_miso

static int pin_cs = PIN_CS_V2;
static int pin_clk = PIN_CLK_V2;
static int pin_mosi = PIN_MOSI_V2;
static int pin_miso = PIN_MISO_V2;

/* NOTE: CPOL=1, CPHA=1 */

void accel_spi_init(void)
{
//	CMU_ClockEnable(cmuClock_HFPER, true);
//	CMU_ClockEnable(cmuClock_USART0, true);
	CMU_ClockEnable(cmuClock_GPIO, true);

//	USART_InitSync_TypeDef initSync = USART_INITSYNC_DEFAULT;
//	initSync.master = true;
//	initSync.msbf = true;
//	initSync.clockMode = usartClockMode0; /* Clock idle low, sample on rising edge. */
//	USART_InitSync(USART0, &initSync);
//
//	USART0->ROUTE = USART_ROUTE_RXPEN | USART_ROUTE_TXPEN | USART_ROUTE_CLKPEN | RADIO_LOCATION;

//	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_TX_PORT(RADIO_LOCATION), AF_USART0_TX_PIN(RADIO_LOCATION), gpioModePushPull, 0);
//	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_RX_PORT(RADIO_LOCATION), AF_USART0_RX_PIN(RADIO_LOCATION), gpioModeInput, 0);
//	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_CS_PORT(RADIO_LOCATION), AF_USART0_CS_PIN(RADIO_LOCATION), gpioModePushPull, 1);
//	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_CLK_PORT(RADIO_LOCATION), AF_USART0_CLK_PIN(RADIO_LOCATION), gpioModePushPull, 0);

	GPIO_PinModeSet(PORT_MOSI, PIN_MOSI, gpioModeDisabled, 0);
	GPIO_PinModeSet(PORT_MISO, PIN_MISO, gpioModeDisabled, 0);
	GPIO_PinModeSet(PORT_CLK,  PIN_CLK,  gpioModeDisabled, 1);
	GPIO_PinModeSet(PORT_CS,   PIN_CS_V1, gpioModeDisabled, 1);
	GPIO_PinModeSet(PORT_CS,   PIN_CS_V2, gpioModeDisabled, 1);
}

void accel_spi_version(int version)
{
	GPIO_PinModeSet(PORT_MOSI, PIN_MOSI, gpioModeDisabled, 0);
	GPIO_PinModeSet(PORT_MISO, PIN_MISO, gpioModeDisabled, 0);
	GPIO_PinModeSet(PORT_CLK,  PIN_CLK,  gpioModeDisabled, 1);
	GPIO_PinModeSet(PORT_CS,   PIN_CS,   gpioModeDisabled, 1);

	switch (version) {
	case 1:
		pin_cs = PIN_CS_V1;
		pin_clk = PIN_CLK_V1;
		pin_mosi = PIN_MOSI_V1;
		pin_miso = PIN_MISO_V1;
		break;
	case 2:
	default:
		pin_cs = PIN_CS_V2;
		pin_clk = PIN_CLK_V2;
		pin_mosi = PIN_MOSI_V2;
		pin_miso = PIN_MISO_V2;
		break;
	}
	GPIO_PinModeSet(PORT_MOSI, PIN_MOSI, gpioModePushPull, 0);
	GPIO_PinModeSet(PORT_MISO, PIN_MISO, gpioModeInput, 0);
	GPIO_PinModeSet(PORT_CLK,  PIN_CLK,  gpioModePushPull, 1);
	GPIO_PinModeSet(PORT_CS,   PIN_CS,   gpioModePushPull, 1);
}

void accel_delay(void)
{
	/* We don't need to slow things down much. A couple of clock cycles
	 * is plenty.
	 */
    volatile int count = 0;
    (void) count;
}

void accel_spi_start(void)
{
	GPIO_PinOutClear (PORT_CS, PIN_CS);
}

void accel_spi_stop(void)
{
	GPIO_PinOutSet (PORT_CS, PIN_CS);
}

void accel_spi_write(uint8_t data)
{
	int i;
	for (i = 0; i < 8; i++) {
		GPIO_PinOutClear (PORT_CLK, PIN_CLK);
		if (data & 0x80)
			GPIO_PinOutSet (PORT_MOSI, PIN_MOSI);
		else
			GPIO_PinOutClear (PORT_MOSI, PIN_MOSI);
		data = data << 1;
		accel_delay();
		GPIO_PinOutSet (PORT_CLK, PIN_CLK);
		accel_delay();
	}
}

uint8_t accel_spi_read(void)
{
	int i;
	uint8_t data = 0;
	GPIO_PinOutClear (PORT_MOSI, PIN_MOSI);
	for (i = 0; i < 8; i++) {
		GPIO_PinOutClear (PORT_CLK, PIN_CLK);
		data = data << 1;
		accel_delay();
		GPIO_PinOutSet (PORT_CLK, PIN_CLK);
		data = data | GPIO_PinInGet (PORT_MISO, PIN_MISO);
		accel_delay();
	}
	return data;
}
