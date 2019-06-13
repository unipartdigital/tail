/* timer.c */

#include "common.h"

#include "timer.h"
#include "em_timer.h"
#include "em_cmu.h"

static uint32_t frequency;

static void (*handler)(void);
static volatile bool running;

void TIMER0_IRQHandler(void)
{
	TIMER_IntClear(TIMER0, TIMER_IntGet(TIMER0));
	running = false;
        if (handler != NULL)
            handler();
}

void timer_init(void)
{
	TIMER_Init_TypeDef init = {
            .ati = false,
            .clkSel = timerClkSelHFPerClk,
            .count2x = false,
            .debugRun = false,
            .dmaClrAct = false,
            .enable = false,
            .fallAction = timerInputActionNone,
            .mode = timerModeUp,
            .oneShot = true,
            .prescale = timerPrescale16,
            .quadModeX4 = false,
            .riseAction = timerInputActionNone,
            .sync = false
        };

        CMU_ClockEnable(cmuClock_HFPER, true);
	CMU_ClockEnable(cmuClock_TIMER0, true);

    running = false;

	TIMER_Init(TIMER0, &init);

	NVIC_EnableIRQ(TIMER0_IRQn);
        TIMER_IntClear(TIMER0, TIMER_IF_OF);
        TIMER_IntEnable(TIMER0, TIMER_IF_OF);
        frequency = CMU_ClockFreqGet(cmuClock_TIMER0) / 16;
}

void timer_sethandler(void (*fn)(void))
{
        handler = fn;
}

void timer_deinit(void)
{
        NVIC_DisableIRQ(TIMER0_IRQn);
        TIMER_IntDisable(TIMER0, TIMER_IF_OF);
        CMU_ClockEnable(cmuClock_TIMER0, false);
}

uint32_t timer_frequency(void)
{
        return frequency;
}

void timer_set(uint32_t delay)
{
        TIMER_TopSet(TIMER0, delay);
}

uint32_t timer_get(void)
{
    return TIMER_CounterGet(TIMER0);
}

void timer_start(void)
{
	running = true;
        TIMER_Enable(TIMER0, true);
}

void timer_stop(void)
{
        TIMER_Enable(TIMER0, false);
        running = false;
        TIMER_CounterSet(TIMER0, 0);
}

bool timer_prepare_sleep(void)
{
	return !running;
}
