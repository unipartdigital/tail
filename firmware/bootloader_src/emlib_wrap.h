/* emlib_wrap.h */
#ifndef _EMLIB_WRAP_H
#define _EMLIB_WRAP_H
#include <stdint.h>

#define __IOM volatile
#define __IM volatile const

#include "em_gpio.h"
#include "em_leuart.h"
#include "em_emu.h"
#include "em_cmu.h"

#if (LEUART_COUNT == 1)
#define LEUART_REF_VALID(ref)    ((ref) == LEUART0)
#elif (LEUART_COUNT == 2)
#define LEUART_REF_VALID(ref)    (((ref) == LEUART0) || ((ref) == LEUART1))
#else
#error "Undefined number of low energy UARTs (LEUART)."
#endif


void LEUART_BaudrateSet(LEUART_TypeDef *leuart,
                        uint32_t refFreq,
                        uint32_t baudrate);
__STATIC_INLINE void LEUART_Sync(LEUART_TypeDef *leuart, uint32_t mask);
void LEUART_Tx(LEUART_TypeDef *leuart, uint8_t data);
void LEUART_Init(LEUART_TypeDef *leuart, LEUART_Init_TypeDef const *init);
void GPIO_PinModeSet(GPIO_Port_TypeDef port,
                     unsigned int pin,
                     GPIO_Mode_TypeDef mode,
                     unsigned int out);
void RMU_ResetCauseClear(void);
void EMU_EnterEM2(bool restore);
#endif /* _EMLIB_WRAP_H */
