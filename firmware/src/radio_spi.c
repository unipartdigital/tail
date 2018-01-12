#include "em_device.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_usart.h"

#include "radio_spi.h"

#define RADIO_LOCATION USART_ROUTE_LOCATION_LOC0
#define RADIO_BITRATE_SLOW 3000000
#define RADIO_BITRATE_FAST 20000000

void radio_spi_init(void)
{
	CMU_ClockEnable(cmuClock_HFPER, true);
	CMU_ClockEnable(cmuClock_USART0, true);
	CMU_ClockEnable(cmuClock_GPIO, true);

	USART_InitSync_TypeDef initSync = USART_INITSYNC_DEFAULT;
	initSync.master = true;
	initSync.msbf = true;
	initSync.baudrate = RADIO_BITRATE_SLOW;
	initSync.clockMode = usartClockMode0; /* Clock idle low, sample on rising edge. */
	USART_InitSync(USART0, &initSync);

	USART0->ROUTE = USART_ROUTE_RXPEN | USART_ROUTE_TXPEN | USART_ROUTE_CLKPEN | RADIO_LOCATION;

	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_TX_PORT(RADIO_LOCATION), AF_USART0_TX_PIN(RADIO_LOCATION), gpioModePushPull, 0);
	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_RX_PORT(RADIO_LOCATION), AF_USART0_RX_PIN(RADIO_LOCATION), gpioModeInput, 0);
	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_CS_PORT(RADIO_LOCATION), AF_USART0_CS_PIN(RADIO_LOCATION), gpioModePushPull, 1);
	GPIO_PinModeSet((GPIO_Port_TypeDef)AF_USART0_CLK_PORT(RADIO_LOCATION), AF_USART0_CLK_PIN(RADIO_LOCATION), gpioModePushPull, 0);
}

void radio_spi_speed(bool fast)
{
	USART_BaudrateSyncSet(USART0, 0, fast?RADIO_BITRATE_FAST:RADIO_BITRATE_SLOW);
}

void radio_spi_start(void)
{
	GPIO_PinOutClear ((GPIO_Port_TypeDef)AF_USART0_CS_PORT(RADIO_LOCATION), AF_USART0_CS_PIN(RADIO_LOCATION));
}

void radio_spi_stop(void)
{
	GPIO_PinOutSet ((GPIO_Port_TypeDef)AF_USART0_CS_PORT(RADIO_LOCATION), AF_USART0_CS_PIN(RADIO_LOCATION));
}

#if 0
static inline uint8_t radio_spi_transfer(uint8_t data)
{
  while (!(USART0->STATUS & USART_STATUS_TXBL))
    ;
  USART0->TXDATA = (uint32_t)data;
  while (!(USART0->STATUS & USART_STATUS_TXC))
    ;
  return (uint8_t)USART0->RXDATA;
}
#endif

#if 0
void radio_spi_write(uint8_t data)
{
	USART_Tx(USART0, data);
    (void) USART_Rx(USART0);
}
uint8_t radio_spi_read(void)
{
	USART_Tx(USART0, 0);
	return USART_Rx(USART0);
}
#endif

#if 0
void radio_spi_write(uint8_t data)
{
	(void) USART_SpiTransfer(USART0, data);
}
uint8_t radio_spi_read(void)
{
	return USART_SpiTransfer(USART0, 0);
}
#endif
