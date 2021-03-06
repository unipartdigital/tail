/**************************************************************************//**
 * @file bootloader.c
 * @brief EFM32 Bootloader. Preinstalled on all new EFM32 devices
 * @version 1.74
 ******************************************************************************
 * @section License
 * <b>Copyright 2015 Silicon Laboratories, Inc. http://www.silabs.com</b>
 *******************************************************************************
 *
 * This file is licensed under the Silabs License Agreement. See the file
 * "Silabs_License_Agreement.txt" for details. Before using this software for
 * any purpose, you must agree to the terms of that agreement.
 *
 ******************************************************************************/

#include <stdbool.h>
#include "em_device.h"
#include "usart.h"
#include "xmodem.h"
#include "boot.h"
//#include "debuglock.h"
//#include "autobaud.h"
#include "crc.h"
#include "config.h"
#include "flash.h"
#include "gcc_bootloader_hacks.h"

#ifndef NDEBUG
#include "debug.h"
#include <stdio.h>
#endif

// Version string, used when the user connects
#if !defined( BOOTLOADER_VERSION_STRING )
#error "No bootloader version string defined !"
#endif

// Vector table in RAM. We construct a new vector table to conserve space in
// flash as it is sparsly populated.
#pragma location=0x20000000
__attribute__((section("vtable")))
#if (_SILICON_LABS_32B_SERIES_1_CONFIG == 2) \
  || (_SILICON_LABS_32B_SERIES_1_CONFIG == 3) \
  || ((_SILICON_LABS_32B_SERIES_1_CONFIG == 1) && defined(_EFM32_GIANT_FAMILY))\
  || ((_SILICON_LABS_32B_SERIES_1_CONFIG == 1) && defined(_EFM32_TINY_FAMILY))
__no_init uint32_t vectorTable[48];
#else
__no_init uint32_t vectorTable[47];
#endif

// This variable holds the computed CRC-16 of the bootloader and is used during
// production testing to ensure the correct programming of the bootloader.
// This can safely be omitted if you are rolling your own bootloader.
#if (_SILICON_LABS_32B_SERIES_1_CONFIG == 2) \
  || (_SILICON_LABS_32B_SERIES_1_CONFIG == 3) \
  || ((_SILICON_LABS_32B_SERIES_1_CONFIG == 1) && defined(_EFM32_GIANT_FAMILY))\
  || ((_SILICON_LABS_32B_SERIES_1_CONFIG == 1) && defined(_EFM32_TINY_FAMILY))
#pragma location=0x200000c0
#else
#pragma location=0x200000bc
#endif
__attribute__((section("bootloadercrc")))
__no_init uint16_t bootloaderCRC;

// If this flag is set the bootloader will be reset when the RTC expires.
// This is used when autobaud is started. If there has been no synchronization
// until the RTC expires the entire bootloader is reset.
// Essentially, this makes the RTC work as a watchdog timer.
bool resetEFM32onRTCTimeout = false;

// Holds flashsize as read from DI page.
uint32_t flashSize;

__ramfunc __noreturn void commandlineLoop(void);
__ramfunc void verify(uint32_t start, uint32_t end);

#if defined(_SILICON_LABS_32B_SERIES_1)
#define RTC_IRQ           RTCC_IRQn
#define RTC_INT_HANDLER   RTCC_IRQHandler
#define RTC_INT_CLEAR()   RTCC->IFC = _RTCC_IFC_MASK
#define RTC_INT_ENABLE()  RTCC->IEN = RTCC_IEN_CC1
#define RTC_COMPSET(x)    RTCC->CC[1].CCV = (x)
#define RTC_START()       RTCC->CTRL = RTCC_CTRL_DEBUGRUN | RTCC_CTRL_ENABLE \
                                       | RTCC_CTRL_CCV1TOP;                  \
                          RTCC->CC[1].CTRL = RTCC_CC_CTRL_MODE_OUTPUTCOMPARE \
                                             | RTCC_CC_CTRL_ICEDGE_NONE

#else
#define RTC_IRQ           RTC_IRQn
#define RTC_INT_HANDLER   RTC_IRQHandler
#define RTC_INT_CLEAR()   RTC->IFC = RTC_IFC_COMP1 | RTC_IFC_COMP0 | RTC_IFC_OF
#define RTC_INT_ENABLE()  RTC->IEN = RTC_IEN_COMP0
#define RTC_COMPSET(x)    RTC->COMP0 = (x)
#define RTC_START()       RTC->CTRL = RTC_CTRL_COMP0TOP | RTC_CTRL_DEBUGRUN | RTC_CTRL_EN
#endif

/**************************************************************************//**
 * Strings.
 *****************************************************************************/
uint8_t crcString[]     = "\r\nCRC: ";
uint8_t newLineString[] = "\r\n";
uint8_t readyString[]   = "\r\nReady\r\n";
uint8_t okString[]      = "\r\nOK\r\n";
uint8_t failString[]    = "\r\nFail\r\n";
uint8_t unknownString[] = "\r\n?\r\n";

/**************************************************************************//**
 * @brief RTC IRQ Handler
 *   The RTC is used to keep the power consumption of the bootloader down while
 *   waiting for the pins to settle, or work as a watchdog in the autobaud
 *   sequence.
 *****************************************************************************/
void RTC_INT_HANDLER(void)
{
  RTC_INT_CLEAR();                  // Clear interrupt flags.
  if (resetEFM32onRTCTimeout)       // Check if EFM should be reset on timeout.
  {
#ifndef NDEBUG
    printf("Autobaud Timeout. Resetting EFM32.\r\n");
#endif
    // Write to the Application Interrupt/Reset Command Register to reset
    // the EFM32. See section 9.3.7 in the reference manual.
    SCB->AIRCR = 0x05FA0004;
  }
}

/**************************************************************************//**
 * @brief
 *   This function is an infinite loop. It actively waits for one of the
 *   following conditions to be true:
 *   1) The SWCLK Debug pins is not asserted and a valid application is
 *      loaded into flash.
 *      In this case the application is booted.
 *   OR:
 *   2) The SWCLK pin is asserted and there is an incoming packet
 *      on the USART RX line
 *      In this case we start sensing to measure the baudrate of incoming packets.
 *
 *   If none of these conditions are met, the EFM32G is put to EM2 sleep for
 *   250 ms.
 *****************************************************************************/
static void waitForBootOrUSART(void)
{
  // Initialize RTC/RTCC.
  RTC_INT_CLEAR();                    // Clear interrupt flags.
  RTC_COMPSET((PIN_LOOP_INTERVAL * LFXO_FREQ) / 1000); // 250 ms wakeup time.
  RTC_INT_ENABLE();                   // Enable interrupt on compare channel.
  NVIC_EnableIRQ(RTC_IRQ);            // Enable RTC interrupt.
  RTC_START();                        // Start RTC.

  for (int i = 0; i < PIN_LOOP_COUNT; i++)
  {
	  // Go to EM2 and wait for RTC wakeup.
	  SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
	  __WFI();

      if (USART_rxByteNoDelay() == BOOTLOADER_ENTERCHAR)
  		  return;

  }
  if (BOOT_checkFirmwareIsValid())
      BOOT_boot();
}

/**************************************************************************//**
 * @brief
 *   Helper function to print flash write verification using CRC
 * @param start
 *   The start of the block to calculate CRC of.
 * @param end
 *   The end of the block. This byte is not included in the checksum.
 *****************************************************************************/
__ramfunc void verify(uint32_t start, uint32_t end)
{
  USART_printString(crcString);
  USART_printHex(CRC_calc((void *) start, (void *) end));
  USART_printString(newLineString);
}

/**************************************************************************//**
 * @brief
 *   The main command line loop. Placed in Ram so that it can still run after
 *   a destructive write operation.
 *   NOTE: __ramfunc is a IAR specific instruction to put code into RAM.
 *   This allows the bootloader to survive a destructive upload.
 *****************************************************************************/
__ramfunc __noreturn void commandlineLoop(void)
{
  uint8_t  c;
#if 0
  uint8_t *returnString;
#endif

  while (1)                                     // The main command loop.
  {
    c = USART_rxByte();                         // Retrieve new character.
    if (c != 0)
    {
      USART_txByte(c);                          // Echo the char
    }
    switch (c)
    {
    case 'u':                                   // Upload.
      USART_printString(readyString);
      XMODEM_download(APPLICATION_START_ADDR, flashSize - CONFIG_SIZE);
      break;

    case 'd':                                   // Destructive upload.
      USART_printString(readyString);
#if defined(_SILICON_LABS_32B_SERIES_1)
      // Treat destructive upload on series 1 as bootloader overwrite.
      XMODEM_download(BOOTLOADER_START_ADDR,
                      BOOTLOADER_START_ADDR + BOOTLOADER_SIZE);
#else
      XMODEM_download(BOOTLOADER_START_ADDR, flashSize - CONFIG_SIZE);
#endif
      break;

    case 't':                                   // Write to user page.
      USART_printString(readyString);
      XMODEM_download(USER_PAGE_START_ADDR, USER_PAGE_END_ADDR);
      break;

#if 0
    case 'p':                                   // Write to lock bits.
#if defined( CoreDebug )        // In core_cmX.h.
      DEBUGLOCK_startDebugInterface();
#endif
      USART_printString(readyString);
#if defined(USART_OVERLAPS_WITH_BOOTLOADER) && defined( CoreDebug )
      // Since the UART overlaps, the bit-banging in
      // DEBUGLOCK_startDebugInterface() will generate some traffic. To avoid
      // interpreting this as UART communication, we need to flush the
      // UART data buffers.
      BOOTLOADER_USART->CMD = BOOTLOADER_USART_CLEARRX;
#endif
      XMODEM_download(LOCK_PAGE_START_ADDR, LOCK_PAGE_END_ADDR);
      break;
#endif

    case 'b':                                   // Boot into new program.
      BOOT_boot();
      break;

#if 0
    case 'l':                                   // Debug lock.
#if !defined(NDEBUG) && defined( CoreDebug )
      // We check if there is a debug session active in DHCSR. If there is we
      // abort the locking. This is because we wish to make sure that the debug
      // lock functionality works without a debugger attatched.
      if ((CoreDebug->DHCSR & CoreDebug_DHCSR_C_DEBUGEN_Msk) != 0x0)
      {
        printf("\r\n\r\n **** WARNING: DEBUG SESSION ACTIVE. NOT LOCKING!  **** \r\n\r\n");
        USART_printString("Debug active.\r\n");
      }
      else
      {
        printf("Starting debug lock sequence.\r\n");
#endif
        if (DEBUGLOCK_lock())
        {
          returnString = okString;
        }
        else
        {
          returnString = failString;
        }
        USART_printString(returnString);

#if !defined(NDEBUG) && defined( CoreDebug )
        printf("Debug lock word: 0x%x \r\n", *(uint32_t *)DEBUG_LOCK_WORD_ADDR);
      }
#endif
      break;
#endif

    case 'v':             // Verify content by calculating CRC of entire flash.
      verify(0, flashSize);
      break;

    case 'c':             // Verify content by calculating CRC of application area.
      verify(APPLICATION_START_ADDR, flashSize - CONFIG_SIZE);
      break;

    case 'n':             // Verify content by calculating CRC of user page.
      verify(USER_PAGE_START_ADDR, USER_PAGE_END_ADDR);
      break;

    case 'm':             // Verify content by calculating CRC of lock page.
      verify(LOCK_PAGE_START_ADDR, LOCK_PAGE_END_ADDR);
      break;

    case 'r':             // Reset command.
      // Write to the Application Interrupt/Reset Command Register to reset
      // the EFM32. See section 9.3.7 in the reference manual.
      SCB->AIRCR = 0x05FA0004;
      break;

      break;

    default:
      USART_printString(unknownString);
    case 0:               // Unknown command.
      // Timeout waiting for RX - avoid printing the unknown string.
      break;
    }
  }
}

extern void exit(int);
/**************************************************************************//**
 * @brief  Create a new vector table in RAM.
 *         We generate it here to conserve space in flash.
 *****************************************************************************/
static void generateVectorTable(void)
{
    for (int i = 0; i < (sizeof(vectorTable)/sizeof(vectorTable[0])); i++)
        vectorTable[i] = (uint32_t) exit;

#if defined(_SILICON_LABS_32B_SERIES_1)
  vectorTable[RTC_IRQ + 16]             = (uint32_t)RTC_INT_HANDLER;

#else
//  vectorTable[AUTOBAUD_TIMER_IRQn + 16] = (uint32_t) TIMER_IRQHandler;
  vectorTable[RTC_IRQ + 16]             = (uint32_t)RTC_INT_HANDLER;
#ifdef USART_OVERLAPS_WITH_BOOTLOADER
//  vectorTable[GPIO_EVEN_IRQn + 16]      = (uint32_t) GPIO_IRQHandler;
#endif
#endif
  SCB->VTOR                             = (uint32_t)vectorTable;
}

/**************************************************************************//**
 * @brief  Main function
 *****************************************************************************/
__noreturn void main(void)
{
#if !defined(_SILICON_LABS_32B_SERIES_1)
  uint32_t periodTime24_8;
  uint32_t tuning;
#endif
#if !defined(_SILICON_LABS_32B_SERIES_1) || !defined(NDEBUG)
  uint32_t clkdiv;
#endif

  // Generate a new vector table and place it in RAM.
  generateVectorTable();

  // Calculate CRC16 for the bootloader itself and the Device Information page.
  // This is used for production testing and can safely be omitted in
  // your own code.
  bootloaderCRC  = CRC_calc((void *)BOOTLOADER_START_ADDR,
                            (void *)BOOTLOADER_END_ADDR);
  bootloaderCRC |= CRC_calc((void *)(DEVINFO_START_ADDR + 2),
                            // Skip first 2 bytes, they are DEVINFO crc.
                            (void *)DEVINFO_END_ADDR)
                   << 16;
  // End safe to omit.

  // Enable clocks for peripherals.
#if defined(_SILICON_LABS_32B_SERIES_1)
  CMU->CTRL        = CMU_CTRL_HFPERCLKEN;
  CMU->HFBUSCLKEN0 = CMU_HFBUSCLKEN0_GPIO | CMU_HFBUSCLKEN0_LE
                     | CMU_HFBUSCLKEN0_LDMA;

  // Enable LFRCO for RTC.
  CMU->LFECLKSEL = CMU_LFECLKSEL_LFE_LFRCO;
  CMU->LFECLKEN0 = CMU_LFECLKEN0_RTCC;
  CMU->OSCENCMD  = CMU_OSCENCMD_LFRCOEN;
#else
#if 0
  CMU->HFPERCLKDIV = CMU_HFPERCLKDIV_HFPERCLKEN;
  CMU->HFPERCLKEN0 = CMU_HFPERCLKEN0_GPIO | BOOTLOADER_USART_CLOCKEN |
                     AUTOBAUD_TIMER_CLOCK ;

  // Enable LE and DMA interface.
  CMU->HFCORECLKEN0 = CMU_HFCORECLKEN0_LE | CMU_HFCORECLKEN0_DMA;

  // Enable LFRCO for RTC.
  CMU->OSCENCMD = CMU_OSCENCMD_LFRCOEN;
  // Setup LFA to use LFRCRO.
  CMU->LFCLKSEL = CMU_LFCLKSEL_LFA_LFRCO | CMU_LFCLKSEL_LFB_HFCORECLKLEDIV2;
  // Enable RTC.
  CMU->LFACLKEN0 = CMU_LFACLKEN0_RTC;
#else
  // Tail configuration here
  CMU->HFPERCLKDIV = CMU_HFPERCLKDIV_HFPERCLKEN;
  CMU->HFPERCLKEN0 = CMU_HFPERCLKEN0_GPIO | BOOTLOADER_USART_CLOCKEN;
  CMU->HFCORECLKEN0 = CMU_HFCORECLKEN0_LE | CMU_HFCORECLKEN0_DMA;
  CMU->OSCENCMD = CMU_OSCENCMD_LFXOEN;
  CMU->LFCLKSEL = CMU_LFCLKSEL_LFA_LFXO | CMU_LFCLKSEL_LFB_LFXO;
  CMU->LFACLKEN0 = CMU_LFACLKEN0_RTC;
#endif
#endif

  // Find the size of the flash. DEVINFO->MSIZE is the size in KB,
  // so left shift by 10.
  flashSize = ((DEVINFO->MSIZE & _DEVINFO_MSIZE_FLASH_MASK)
               >> _DEVINFO_MSIZE_FLASH_SHIFT)
              << 10;

#ifndef NDEBUG
  DEBUG_init();
  printf("\r\n\r\n *** Debug output enabled. ***\r\n\r\n");
#endif

  CONFIG_UsartGpioSetupRxOnly();

  // Enable LEUART.
  CMU->LFBCLKEN0 = BOOTLOADER_LEUART_CLOCKEN;

  periodTime24_8 = 1744; /* 9600 baud, in theory */
  clkdiv = (periodTime24_8 >> 1) - 256;

  // Initialize the UART.
  USART_init(clkdiv);

  // Wait for a boot operation.
  waitForBootOrUSART();

#if defined (_DEVINFO_HFRCOCAL1_BAND28_MASK)
  // Change to 28MHz internal oscillator to increase speed of
  // bootloader.
  tuning = (DEVINFO->HFRCOCAL1 & _DEVINFO_HFRCOCAL1_BAND28_MASK)
           >> _DEVINFO_HFRCOCAL1_BAND28_SHIFT;

  CMU->HFRCOCTRL = CMU_HFRCOCTRL_BAND_28MHZ | tuning;
#ifndef NDEBUG
  // Set new clock division based on the 28Mhz clock.
  DEBUG_USART->CLKDIV = 3634;
#endif

#elif defined(_DEVINFO_HFRCOCAL1_BAND21_MASK)
  // Change to 21MHz internal oscillator to increase speed of
  // bootloader.
  tuning = ((DEVINFO->HFRCOCAL1 & _DEVINFO_HFRCOCAL1_BAND21_MASK)
           >> _DEVINFO_HFRCOCAL1_BAND21_SHIFT);

  CMU->HFRCOCTRL = CMU_HFRCOCTRL_BAND_21MHZ | tuning;
#ifndef NDEBUG
  // Set new clock division based on the 21Mhz clock.
  DEBUG_USART->CLKDIV = 2661;
#endif

#else
#error "Can not make correct clock selection."
#endif

  // Setup pins for USART.
  CONFIG_UsartGpioSetup();

  // When autobaud has completed, we can be fairly certain that
  // the entry into the bootloader is intentional so we can disable the timeout.
  NVIC_DisableIRQ(RTC_IRQ);

  // Print a message to show that we are in bootloader mode.
  USART_printString((uint8_t *)"\r\n\r\n" BOOTLOADER_VERSION_STRING  " ChipID: ");
  // Print the chip ID. This is useful for production tracking.
  USART_printHex(DEVINFO->UNIQUEH);
  USART_printHex(DEVINFO->UNIQUEL);
  USART_printString((uint8_t *)"\r\n");

  // Initialize flash for writing.
  FLASH_init();

  // Start executing command line.
  commandlineLoop();
}
