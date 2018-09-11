#include "em_device.h"
#include "em_chip.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_leuart.h"
#include "em_emu.h"

#include "common.h"
#include "radio.h"
#include "radio_spi.h"
#include "radio_reg.h"
#include "accel.h"
#include "uart.h"
#include "cli.h"
#include "time.h"
#include "config.h"
#include "proto.h"

#define ROLE_TAG 1
#define ROLE_ANCHOR 2
#define ROLE_RANCHOR 3
#define ROLE_TAGIPV6 6

#define CLOCK_DEBUG 0

/* XXX no longer used */
#define ANTENNA_DELAY_TX 16434
#define ANTENNA_DELAY_RX 16434

radio_config_t radio_config = {
		/* chan */        5,
		/* prf_high */    false,
		/* tx_plen */     RADIO_PLEN_128,
		/* rx_pac */      RADIO_PAC_8,
		/* tx_pcode */    4,
		/* rx_pcode */    4,
		/* ns_sfd */      false,
		/* data_rate */   RADIO_RATE_6M8,
		/* long_frames */ false,
		/* sfd_timeout */ 0
};


uint8_t xtal_trim;

void int_init(void)
{
	/* PC9 is the radio, PC4 is the accelerometer */
    GPIO_PinModeSet(gpioPortC, 4, gpioModeInput, 0);
    /* Set rising edge interrupt for both pins */
    GPIO_IntConfig(gpioPortC, 4, true, false, true);
    /* Enable interrupt in core for even and odd gpio interrupts */
    NVIC_ClearPendingIRQ(GPIO_EVEN_IRQn);
    NVIC_EnableIRQ(GPIO_EVEN_IRQn);
}

int gpio_even = 0;

void GPIO_EVEN_IRQHandler(void)
{
    GPIO_IntClear(GPIO_IntGet());
    gpio_even++;
}

extern void *__StackTop;
extern void *__StackLimit;
extern void *__HeapLimit;
extern void *__HeapBase;

int main(void)
{
  /* Chip errata */
  CHIP_Init();
  /* Enable oscillator here so that we can do other initialisation while
   * it is stabilising. uart_init() will block until the oscillator is
   * stabilised.
   */
  CMU_OscillatorEnable(cmuOsc_LFXO, true, false);

  memset(&__HeapBase, 0x5A, &__StackTop - &__HeapBase - 0x100);

  CMU_HFRCOBandSet(cmuHFRCOBand_21MHz);

  CMU_ClockEnable(cmuClock_GPIO, true);

  GPIO_PinModeSet(gpioPortA, 0, gpioModePushPull, 1);

#if CLOCK_DEBUG
  /* Select HFRCO as source for CMU_CLK0 pin */
    CMU->CTRL =(CMU->CTRL &~_CMU_CTRL_CLKOUTSEL0_MASK)| CMU_CTRL_CLKOUTSEL0_HFRCO;
//    CMU->CTRL =(CMU->CTRL &~_CMU_CTRL_CLKOUTSEL1_MASK)| CMU_CTRL_CLKOUTSEL1_HFCLK;
//    CMU->CTRL =(CMU->CTRL &~_CMU_CTRL_CLKOUTSEL0_MASK)| CMU_CTRL_CLKOUTSEL0_HFRCO;
//    CMU->CTRL =(CMU->CTRL &~_CMU_CTRL_CLKOUTSEL1_MASK)| CMU_CTRL_CLKOUTSEL1_LFRCO;
    CMU->CTRL =(CMU->CTRL &~_CMU_CTRL_CLKOUTSEL1_MASK)| CMU_CTRL_CLKOUTSEL1_LFXO;
  CMU->ROUTE = CMU_ROUTE_LOCATION_LOC0 | CMU_ROUTE_CLKOUT0PEN | CMU_ROUTE_CLKOUT1PEN;
  /* Configure PA12 as push-pull output */
  GPIO_PinModeSet(gpioPortA, 2, gpioModePushPull ,0);
  GPIO_PinModeSet(gpioPortA, 1, gpioModePushPull ,0);
#endif
  GPIO_PinModeSet(gpioPortA, 1, gpioModePushPull ,0);

  /* Battery monitor disable - saves a couple of microamps */
  GPIO_PinModeSet(gpioPortD, 7, gpioModePushPull, 0);

  int_init();

  delay(100);
  time_init();
  config_init();
  radio_init(true);
  accel_init();

  xtal_trim = 0x10; // Default value in radio driver
  if (config_get(config_key_xtal_trim, &xtal_trim, 1))
	  radio_xtal_trim(xtal_trim);

  /* Defer uart_init() until the latest possible time, because it will wait
   * for the LFXO to be stable.
   */
  uart_init();
  cli_init();

  uint8_t accel_status = accel_read(0x08);
  uint8_t accel_init = accel_read(0x0f);

  write_hex(accel_status);
  write_string(":");
  write_hex(accel_init);
  write_string("\r\n");

#if 0
  uint8_t seq[] = {8, 4, 1, 2, 0, 2, 1, 4, 8, 0};

  /* Infinite loop */
  while (0) {
	  uint8_t data[4];
	  data[0] = 0;
	  data[1] = 0;
	  data[2] = 0;
	  data[3] = 0;
	  data[0] = accel_read(0x08); /* Status 1 */
	  data[0] = accel_read(0x0F); /* Init 1 */
	  /* Set pins to outputs */
	  radio_write32(RREG(GPIO_DIR), FIELDS(GPIO_DIR, GDM0, 1, GDM1, 1, GDM2, 1, GDM3, 1, GDP0, 0, GDP1, 0, GDP2, 0, GDP3, 0));
	  for (int i = 0; i < ARRAY_SIZE(seq); i++) {
	      /* Set pins high */
	      data[0] = 0xf0 + seq[i];
	      radio_write32(RREG(GPIO_DOUT), 0xf0 + seq[i]);
	      delay(100);
	  }
  }
#endif

    radio_leds(true, 1);

    uint8_t byte;

    (void) config_get(config_key_chan, &radio_config.chan, sizeof(radio_config.chan));
    if (config_get(config_key_prf_high, &byte, 1) > 0)
    	radio_config.prf_high = byte?true:false;
    (void) config_get(config_key_tx_plen, &radio_config.tx_plen, sizeof(radio_config.tx_plen));
    (void) config_get(config_key_rx_pac, &radio_config.rx_pac, sizeof(radio_config.rx_pac));
    (void) config_get(config_key_tx_pcode, &radio_config.tx_pcode, sizeof(radio_config.tx_pcode));
    (void) config_get(config_key_rx_pcode, &radio_config.rx_pcode, sizeof(radio_config.rx_pcode));
    if (config_get(config_key_ns_sfd, &byte, 1) > 0)
    	radio_config.ns_sfd = byte?true:false;
    (void) config_get(config_key_data_rate, &radio_config.data_rate, sizeof(radio_config.data_rate));
    if (config_get(config_key_long_frames, &byte, 1) > 0)
    	radio_config.long_frames = byte?true:false;
    (void) config_get(config_key_sfd_timeout, (uint8_t *)&radio_config.sfd_timeout, sizeof(radio_config.sfd_timeout));


    radio_configure(&radio_config);

    radio_spi_speed(true);

    set_antenna_delay_tx(config_get16(config_key_antenna_delay_tx));
    set_antenna_delay_rx(config_get16(config_key_antenna_delay_rx));

    uint32_t word = 0;

    if (config_get(config_key_tx_power, (uint8_t *)&word, 4) > 0)
    	radio_settxpower(word);
    if (config_get(config_key_smart_tx_power, &byte, 1) > 0)
    	radio_smarttxpowercontrol(byte);

    word = 0;
    if (config_get(config_key_turnaround_delay, (uint8_t *)&word, 4) > 0)
    	proto_turnaround_delay(word);

    word = 0;
    if (config_get(config_key_rxtimeout, (uint8_t *)&word, 4) > 0)
    	proto_rx_timeout(word);


    proto_init();

    switch (config_get8(config_key_role)) {
    case ROLE_ANCHOR:
        anchor();
        break;
    case ROLE_TAG:
    	tag();
    	break;
    case ROLE_RANCHOR:
    	ranchor();
    	break;
    case ROLE_TAGIPV6:
    	tagipv6();
    	break;
    }

    while (1) {
    	time_event_poll();
        cli_poll();
        proto_poll();
        if (!cli_prepare_sleep())
        	continue;
        if (!uart_prepare_sleep())
        	continue;
        if (!time_prepare_sleep())
        	continue;
        EMU_EnterEM2(true);
    }
}
