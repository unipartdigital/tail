#include "em_device.h"
#include "em_chip.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_leuart.h"
#include "em_emu.h"
#include "em_rmu.h"

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
#include "timer.h"
#include "event.h"
#include "entropy.h"
#include "crypto.h"

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

  delay(100);
  event_clear();
  time_init();
  config_init();
  radio_init(true);
  bool accel_present = accel_init();

  xtal_trim = 0x10; // Default value in radio driver
  if (config_get(config_key_xtal_trim, &xtal_trim, 1))
	  radio_xtal_trim(xtal_trim);

  /* Defer uart_init() until the latest possible time, because it will wait
   * for the LFXO to be stable.
   */
  uart_init(config_get8(config_key_uart_drive));

  uint32_t reset_cause = RMU_ResetCauseGet();
  RMU_ResetCauseClear();


#define RMU_RSTCAUSE_PORST_XMASK         0x00000000UL
#define RMU_RSTCAUSE_BODUNREGRST_XMASK   0x00000081UL
#define RMU_RSTCAUSE_BODREGRST_XMASK     0x00000091UL
#define RMU_RSTCAUSE_EXTRST_XMASK        0x00000001UL
#define RMU_RSTCAUSE_WDOGRST_XMASK       0x00000003UL
#define RMU_RSTCAUSE_LOCKUPRST_XMASK     0x0000EFDFUL
#define RMU_RSTCAUSE_SYSREQRST_XMASK     0x0000EF9FUL
#define RMU_RSTCAUSE_EM4RST_XMASK        0x00000719UL
#define RMU_RSTCAUSE_EM4WURST_XMASK      0x00000619UL
#define RMU_RSTCAUSE_BODAVDD0_XMASK      0x0000041FUL
#define RMU_RSTCAUSE_BODAVDD1_XMASK      0x0000021FUL

  if (reset_cause & RMU_RSTCAUSE_PORST)
	  write_string("Power on reset\r\n");
  if (reset_cause & RMU_RSTCAUSE_BODUNREGRST)
	  write_string("Brownout in unregulated domain\r\n");
  if (reset_cause & RMU_RSTCAUSE_BODREGRST)
	  write_string("Brownout in regulated domain\r\n");
  if (reset_cause & RMU_RSTCAUSE_EXTRST)
	  write_string("External reset\r\n");
  if (reset_cause & RMU_RSTCAUSE_WDOGRST)
	  write_string("Watchdog reset\r\n");
  if (reset_cause & RMU_RSTCAUSE_LOCKUPRST)
	  write_string("Lockup reset\r\n");
  if (reset_cause & RMU_RSTCAUSE_SYSREQRST)
	  write_string("System requested reset\r\n");
  if (reset_cause & RMU_RSTCAUSE_EM4RST)
	  write_string("Woke up from EM4\r\n");
  if (reset_cause & RMU_RSTCAUSE_EM4WURST)
	  write_string("Woken from EM4 by pin\r\n");
  if (reset_cause & RMU_RSTCAUSE_BODAVDD0)
	  write_string("Brownout in analogue domain 0\r\n");
  if (reset_cause & RMU_RSTCAUSE_BODAVDD1)
	  write_string("Brownout in analogue domain 1\r\n");

  if (accel_present)
      write_string("Accelerometer detected\r\n");
  else
	  write_string("No accelerometer detected\r\n");

  cli_init();

  uint8_t sniff_sensitivity = 2;
  uint8_t sniff_exponent = 0;
  uint8_t sniff_mode = 1;
  uint8_t sniff_count = 0;
  (void) config_get(config_key_accel_sensitivity, &sniff_sensitivity, 1);
  (void) config_get(config_key_accel_exponent, &sniff_exponent, 1);
  (void) config_get(config_key_accel_mode, &sniff_mode, 1);
  (void) config_get(config_key_accel_count, &sniff_count, 1);
  accel_enter_mode(ACCEL_STANDBY);
  accel_config_power_mode(ACCEL_ULP, ACCEL_ULP);
  accel_config_range_resolution(ACCEL_2G, ACCEL_6BITS);
  accel_config_rate(ACCEL_ULP_ODR_25);
  accel_config_threshold(sniff_sensitivity, sniff_sensitivity, sniff_sensitivity, sniff_exponent);
  if (sniff_count > 0)
      accel_config_detection_count(sniff_count-1, sniff_count-1, sniff_count-1, true);
  else
      accel_config_detection_count(0, 0, 0, false);
  accel_config_sniff_mode(false, sniff_mode);

  accel_enter_mode(ACCEL_SNIFF);

    radio_leds(true, config_get8(config_key_radio_leds));

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
	radio_doublebuffer(true);

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

    word = 0;
    if (config_get(config_key_rxdelay, (uint8_t *)&word, 4) > 0)
        proto_rx_delay(word);

    crypto_init();
    proto_init();

    while (1) {
    	time_event_poll();
        cli_poll();
        proto_poll();
        accel_poll();
        entropy_poll();
        if (!cli_prepare_sleep())
        	continue;
        if (!uart_prepare_sleep())
        	continue;
        if (!time_prepare_sleep())
        	continue;
        if (!timer_prepare_sleep())
        	continue;
        EMU_EnterEM2(true);
    }
}
