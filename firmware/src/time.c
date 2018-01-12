/* time.c */

#include "common.h"

#include "time.h"
#include "em_rtc.h"
#include "em_cmu.h"

#define X(x) 1+
uint32_t time_event_time[TIME_EVENTS 0];
#undef X

#define X(x) x,
time_event_fn time_event_fns[] = {
		TIME_EVENTS
};
#undef X

void RTC_IRQHandler(void)
{
	RTC_IntClear(RTC_IntGet());
	/* We don't really need to do anything else here.
	 * The interrupt will bring the CPU out of sleep mode
	 * and the main loop will poll the time event list.
	 */
}

void time_init(void)
{
	int i;
	RTC_Init_TypeDef init = {true, false, false};

	/* Some of these are probably enabled elsewhere, but... */
	CMU_OscillatorEnable(cmuOsc_LFRCO, true, true);
	CMU_ClockDivSet(cmuClock_RTC, TIME_PRESCALER);
	CMU_ClockSelectSet(cmuClock_LFA, cmuSelect_LFRCO);
	CMU_ClockEnable(cmuClock_RTC, true);
	CMU_ClockEnable(cmuClock_CORELE, true);

	RTC_Init(&init);

	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		time_event_time[i] = TIME_INVALID;
	}

	NVIC_EnableIRQ(RTC_IRQn);
	RTC_IntEnable(RTC_IEN_COMP0);
}

uint32_t time_now(void)
{
	return RTC_CounterGet();
}

/* True if a >= b */
bool time_ge(uint32_t a, uint32_t b)
{
	return ((a - b) & 0xffffff) < 0x800000;
}

uint32_t time_add(uint32_t a, uint32_t b)
{
	return (a + b) & 0xffffff;
}

uint32_t time_sub(uint32_t a, uint32_t b)
{
	return (a - b) & 0xffffff;
}

void time_event_schedule_at(time_event_id index, uint32_t time)
{
	time_event_time[index] = time;
}

void time_event_schedule_in(time_event_id index, uint32_t time)
{
	time = time_add(time, time_now());
	time_event_schedule_at(index, time);
}

void time_event_poll(void)
{
	uint32_t now = time_now();
	int i;

	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		uint32_t event_time = time_event_time[i];
		if (event_time > 0x1000000)
			continue;
		if (time_ge(now, event_time)) {
			time_event_time[i] = TIME_INVALID;
			time_event_fns[i]();
		}
	}
}

bool time_prepare_sleep(void)
{
	uint32_t now = time_now();
	uint32_t remaining = 0xffffffff;
	uint32_t wake_time = now;
	int i;

	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		uint32_t event_time = time_event_time[i];
		uint32_t delta;
		if (event_time > 0x1000000)
			continue;
		if (time_ge(now, event_time)) {
			return false;
		}
		delta = time_sub(event_time, now);
		if (delta < remaining) {
			remaining = delta;
			wake_time = event_time;
		}
	}

	if (remaining > 0x1000000)
		return true; // No plans to wake up, ever.

	if (remaining < TIME_SLEEP_TRHESHOLD)
		return false; // We need to wake up soon anyway.

	RTC_CompareSet(0, wake_time);

	return true;
}
