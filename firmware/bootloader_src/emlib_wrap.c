#include "emlib_wrap.h"

/* em_leuart.c */
void LEUART_FreezeEnable(LEUART_TypeDef *leuart, bool enable)
{
  if (enable)
  {
    /*
     * Wait for any ongoing LF synchronization to complete. This is just to
     * protect against the rare case when a user
     * - modifies a register requiring LF sync
     * - then enables freeze before LF sync completed
     * - then modifies the same register again
     * since modifying a register while it is in sync progress should be
     * avoided.
     */
    while (leuart->SYNCBUSY)
      ;

    leuart->FREEZE = LEUART_FREEZE_REGFREEZE;
  }
  else
  {
    leuart->FREEZE = 0;
  }
}

void LEUART_BaudrateSet(LEUART_TypeDef *leuart,
                        uint32_t refFreq,
                        uint32_t baudrate)
{
  uint32_t          clkdiv;
  CMU_Clock_TypeDef clock;

  /* Inhibit divide by 0 */
  EFM_ASSERT(baudrate);

  /*
   * We want to use integer division to avoid forcing in float division
   * utils, and yet keep rounding effect errors to a minimum.
   *
   * CLKDIV in asynchronous mode is given by:
   *
   * CLKDIV = 256*(fLEUARTn/br - 1) = ((256*fLEUARTn)/br) - 256
   *
   * Normally, with fLEUARTn appr 32768Hz, there is no problem with overflow
   * if using 32 bit arithmetic. However, since fLEUARTn may be derived from
   * HFCORECLK as well, we must consider overflow when using integer arithmetic.
   *
   * The basic problem with integer division in the above formula is that
   * the dividend (256 * fLEUARTn) may become higher than max 32 bit
   * integer. Yet, we want to evaluate dividend first before dividing in
   * order to get as small rounding effects as possible. We do not want
   * to make too harsh restrictions on max fLEUARTn value either.
   *
   * Since the last 3 bits of CLKDIV are don't care, we can base our
   * integer arithmetic on the below formula
   *
   * CLKDIV/8 = ((32*fLEUARTn)/br) - 32
   *
   * and calculate 1/8 of CLKDIV first. This allows for fLEUARTn
   * up to 128MHz without overflowing a 32 bit value!
   */

  /* Get current frequency? */
  if (!refFreq)
  {
    if (leuart == LEUART0)
    {
      clock = cmuClock_LEUART0;
    }
#if (LEUART_COUNT > 1)
    else if (leuart == LEUART1)
    {
      clock = cmuClock_LEUART1;
    }
#endif
    else
    {
      EFM_ASSERT(0);
      return;
    }

    refFreq = CMU_ClockFreqGet(clock);
  }

  /* Calculate and set CLKDIV with fractional bits */
  clkdiv  = (32 * refFreq) / baudrate;
  clkdiv -= 32;
  clkdiv *= 8;

  /* Verify that resulting clock divider is within limits */
  EFM_ASSERT(clkdiv <= _LEUART_CLKDIV_MASK);

  /* If EFM_ASSERT is not enabled, make sure we don't write to reserved bits */
  clkdiv &= _LEUART_CLKDIV_MASK;

  /* LF register about to be modified require sync. busy check */
  LEUART_Sync(leuart, LEUART_SYNCBUSY_CLKDIV);

  leuart->CLKDIV = clkdiv;
}

void LEUART_Init(LEUART_TypeDef *leuart, LEUART_Init_TypeDef const *init)
{
  /* Make sure the module exists on the selected chip */
  EFM_ASSERT(LEUART_REF_VALID(leuart));

  /* LF register about to be modified require sync. busy check */
  LEUART_Sync(leuart, LEUART_SYNCBUSY_CMD);

  /* Ensure disabled while doing config */
  leuart->CMD = LEUART_CMD_RXDIS | LEUART_CMD_TXDIS;

  /* Freeze registers to avoid stalling for LF synchronization */
  LEUART_FreezeEnable(leuart, true);

  /* Configure databits and stopbits */
  leuart->CTRL = (leuart->CTRL & ~(_LEUART_CTRL_PARITY_MASK
                                   | _LEUART_CTRL_STOPBITS_MASK))
                 | (uint32_t)(init->databits)
                 | (uint32_t)(init->parity)
                 | (uint32_t)(init->stopbits);

  /* Configure baudrate */
  LEUART_BaudrateSet(leuart, init->refFreq, init->baudrate);

  /* Finally enable (as specified) */
  leuart->CMD = (uint32_t)init->enable;

  /* Unfreeze registers, pass new settings on to LEUART */
  LEUART_FreezeEnable(leuart, false);
}

__STATIC_INLINE void LEUART_Sync(LEUART_TypeDef *leuart, uint32_t mask)
{
  /* Avoid deadlock if modifying the same register twice when freeze mode is */
  /* activated. */
  if (leuart->FREEZE & LEUART_FREEZE_REGFREEZE)
  {
    return;
  }

  /* Wait for any pending previous write operation to have been completed */
  /* in low frequency domain */
  while (leuart->SYNCBUSY & mask)
    ;
}

void LEUART_Tx(LEUART_TypeDef *leuart, uint8_t data)
{
  /* Check that transmit buffer is empty */
  while (!(leuart->STATUS & LEUART_STATUS_TXBL))
    ;

  /* LF register about to be modified require sync. busy check */
  LEUART_Sync(leuart, LEUART_SYNCBUSY_TXDATA);

  leuart->TXDATA = (uint32_t)data;
}

/* em_gpio.c */

void GPIO_PinModeSet(GPIO_Port_TypeDef port,
                     unsigned int pin,
                     GPIO_Mode_TypeDef mode,
                     unsigned int out)
{
  EFM_ASSERT(GPIO_PORT_PIN_VALID(port, pin));

  /* If disabling pin, do not modify DOUT in order to reduce chance for */
  /* glitch/spike (may not be sufficient precaution in all use cases) */
  if (mode != gpioModeDisabled)
  {
    if (out)
    {
      GPIO_PinOutSet(port, pin);
    }
    else
    {
      GPIO_PinOutClear(port, pin);
    }
  }

  /* There are two registers controlling the pins for each port. The MODEL
   * register controls pins 0-7 and MODEH controls pins 8-15. */
  if (pin < 8)
  {
    GPIO->P[port].MODEL = (GPIO->P[port].MODEL & ~(0xFu << (pin * 4)))
                          | (mode << (pin * 4));
  }
  else
  {
    GPIO->P[port].MODEH = (GPIO->P[port].MODEH & ~(0xFu << ((pin - 8) * 4)))
                          | (mode << ((pin - 8) * 4));
  }

  if (mode == gpioModeDisabled)
  {
    if (out)
    {
      GPIO_PinOutSet(port, pin);
    }
    else
    {
      GPIO_PinOutClear(port, pin);
    }
  }
}

/* em_rmu.c */
void RMU_ResetCauseClear(void)
{
  RMU->CMD = RMU_CMD_RCCLR;

#if defined(EMU_AUXCTRL_HRCCLR)
  {
    uint32_t locked;

    /* Clear some reset causes not cleared with RMU CMD register */
    /* (If EMU registers locked, they must be unlocked first) */
    locked = EMU->LOCK & EMU_LOCK_LOCKKEY_LOCKED;
    if (locked)
    {
      EMU_Unlock();
    }

    BUS_RegBitWrite(&(EMU->AUXCTRL), _EMU_AUXCTRL_HRCCLR_SHIFT, 1);
    BUS_RegBitWrite(&(EMU->AUXCTRL), _EMU_AUXCTRL_HRCCLR_SHIFT, 0);

    if (locked)
    {
      EMU_Lock();
    }
  }
#endif
}


/* em_emu.c */
typedef enum
{
  emState_Save,         /* Save EMU and CMU state */
  emState_Restore,      /* Restore and unlock     */
} emState_TypeDef;

static void emState(emState_TypeDef action)
{
  uint32_t oscEnCmd;
  uint32_t cmuLocked;
  static uint32_t cmuStatus;
  static CMU_Select_TypeDef hfClock;
#if defined( _EMU_CMD_EM01VSCALE0_MASK )
  static uint8_t vScaleStatus;
#endif


  /* Save or update state */
  if (action == emState_Save)
  {
    /* Save configuration. */
    cmuStatus = CMU->STATUS;
    hfClock = CMU_ClockSelectGet(cmuClock_HF);
#if defined( _EMU_CMD_EM01VSCALE0_MASK )
    /* Save vscale */
    EMU_VScaleWait();
    vScaleStatus   = (uint8_t)((EMU->STATUS & _EMU_STATUS_VSCALE_MASK)
                               >> _EMU_STATUS_VSCALE_SHIFT);
#endif
  }
  else if (action == emState_Restore) /* Restore state */
  {
    /* Apply saved configuration. */
#if defined( _EMU_CMD_EM01VSCALE0_MASK )
    /* Restore EM0 and 1 voltage scaling level. EMU_VScaleWait() is called later,
       just before HF clock select is set. */
    EMU->CMD = vScaleEM01Cmd((EMU_VScaleEM01_TypeDef)vScaleStatus);
#endif

    /* CMU registers may be locked */
    cmuLocked = CMU->LOCK & CMU_LOCK_LOCKKEY_LOCKED;
    CMU_Unlock();

    /* AUXHFRCO are automatically disabled (except if using debugger). */
    /* HFRCO, USHFRCO and HFXO are automatically disabled. */
    /* LFRCO/LFXO may be disabled by SW in EM3. */
    /* Restore according to status prior to entering energy mode. */
    oscEnCmd = 0;
    oscEnCmd |= ((cmuStatus & CMU_STATUS_HFRCOENS)    ? CMU_OSCENCMD_HFRCOEN : 0);
    oscEnCmd |= ((cmuStatus & CMU_STATUS_AUXHFRCOENS) ? CMU_OSCENCMD_AUXHFRCOEN : 0);
    oscEnCmd |= ((cmuStatus & CMU_STATUS_LFRCOENS)    ? CMU_OSCENCMD_LFRCOEN : 0);
    oscEnCmd |= ((cmuStatus & CMU_STATUS_HFXOENS)     ? CMU_OSCENCMD_HFXOEN : 0);
    oscEnCmd |= ((cmuStatus & CMU_STATUS_LFXOENS)     ? CMU_OSCENCMD_LFXOEN : 0);
#if defined( _CMU_STATUS_USHFRCOENS_MASK )
    oscEnCmd |= ((cmuStatus & CMU_STATUS_USHFRCOENS)  ? CMU_OSCENCMD_USHFRCOEN : 0);
#endif
    CMU->OSCENCMD = oscEnCmd;

#if defined( _EMU_STATUS_VSCALE_MASK )
    /* Wait for upscale to complete and then restore selected clock */
    EMU_VScaleWait();
#endif

    if (hfClock != cmuSelect_HFRCO)
    {
      CMU_ClockSelectSet(cmuClock_HF, hfClock);
    }

    /* If HFRCO was disabled before entering Energy Mode, turn it off again */
    /* as it is automatically enabled by wake up */
    if ( ! (cmuStatus & CMU_STATUS_HFRCOENS) )
    {
      CMU->OSCENCMD = CMU_OSCENCMD_HFRCODIS;
    }

    /* Restore CMU register locking */
    if (cmuLocked)
    {
      CMU_Lock();
    }
  }
}

void EMU_EnterEM2(bool restore)
{
#if defined( ERRATA_FIX_EMU_E107_EN )
  bool errataFixEmuE107En;
  uint32_t nonWicIntEn[2];
#endif

  /* Save EMU and CMU state requiring restore on EM2 exit. */
  emState(emState_Save);

#if defined( _EMU_CTRL_EM23VSCALE_MASK )
  vScaleDownEM23Setup();
#endif

  /* Enter Cortex deep sleep mode */
  SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;

  /* Fix for errata EMU_E107 - store non-WIC interrupt enable flags.
     Disable the enabled non-WIC interrupts. */
#if defined( ERRATA_FIX_EMU_E107_EN )
  errataFixEmuE107En = getErrataFixEmuE107En();
  if (errataFixEmuE107En)
  {
    nonWicIntEn[0] = NVIC->ISER[0] & NON_WIC_INT_MASK_0;
    NVIC->ICER[0] = nonWicIntEn[0];
#if (NON_WIC_INT_MASK_1 != (~(0x0U)))
    nonWicIntEn[1] = NVIC->ISER[1] & NON_WIC_INT_MASK_1;
    NVIC->ICER[1] = nonWicIntEn[1];
#endif
  }
#endif

#if defined( ERRATA_FIX_DCDC_FETCNT_SET_EN )
  dcdcFetCntSet(true);
#endif
#if defined( ERRATA_FIX_DCDC_LNHS_BLOCK_EN )
  dcdcHsFixLnBlock();
#endif

  __WFI();

#if defined( ERRATA_FIX_DCDC_FETCNT_SET_EN )
  dcdcFetCntSet(false);
#endif

  /* Fix for errata EMU_E107 - restore state of non-WIC interrupt enable flags. */
#if defined( ERRATA_FIX_EMU_E107_EN )
  if (errataFixEmuE107En)
  {
    NVIC->ISER[0] = nonWicIntEn[0];
#if (NON_WIC_INT_MASK_1 != (~(0x0U)))
    NVIC->ISER[1] = nonWicIntEn[1];
#endif
  }
#endif

  /* Restore oscillators/clocks and voltage scaling if supported. */
  if (restore)
  {
    emState(emState_Restore);
  }
  else
  {
    /* If not restoring, and original clock was not HFRCO, we have to */
    /* update CMSIS core clock variable since HF clock has changed */
    /* to HFRCO. */
    SystemCoreClockUpdate();
  }
}
