#include "em_device.h"
#include "em_chip.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_leuart.h"
#include "em_emu.h"
#include "em_rmu.h"

#include "common.h"
#include "uart.h"
#include "cli.h"
#include "timer.h"

#include "misc.h"

#define CLOCK_DEBUG 0

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
  //time_init();
  //bool accel_present = accel_init();

  /* Defer uart_init() until the latest possible time, because it will wait
   * for the LFXO to be stable.
   */
  uart_init();

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
  write_hex(reset_cause);

  cli_init();

   // proto_init();

    while (1) {
    	//time_event_poll();
        cli_poll();
        //proto_poll();
        //accel_poll();
        if (!cli_prepare_sleep())
        	continue;
        if (!uart_prepare_sleep())
        	continue;
        //if (!time_prepare_sleep())
        //	continue;
        if (!timer_prepare_sleep())
        	continue;
        EMU_EnterEM2(true);
    }
}
