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

static time_event_fn early_wakeup_fn;
static uint32_t early_wakeup_advance;
static uint32_t early_wakeup_time;

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
	early_wakeup_fn = NULL;
	early_wakeup_advance = 0;
	early_wakeup_time = TIME_INVALID;

	NVIC_EnableIRQ(RTC_IRQn);
	RTC_IntEnable(RTC_IEN_COMP0);
}

void time_early_wakeup(time_event_fn function, uint32_t time)
{
	early_wakeup_fn = function;
	early_wakeup_advance = time;
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

/* Set the next early wakeup event that is no earlier than now */
void time_early_wakeup_set_next(uint32_t now)
{
	int i;
	uint32_t wakeup_time = TIME_INVALID;
	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		uint32_t event_time = time_event_time[i];
		uint32_t early;
		if (!TIME_VALID(event_time))
			continue;
		early = time_sub(event_time, early_wakeup_advance);
		if (!time_ge(early, now))
			continue;
		if (time_ge(wakeup_time, early))
			wakeup_time = early;
	}
	early_wakeup_time = wakeup_time;
}

void time_event_schedule_at(time_event_id index, uint32_t time)
{
	uint32_t early;
	uint32_t orig_time = time_event_time[index];

	time_event_time[index] = time;

	if (early_wakeup_fn) {
	    if (TIME_VALID(time)) {
	        early = time_sub(time, early_wakeup_advance);
	        if (TIME_VALID(early_wakeup_time)) {
	    	    if (time_ge(early_wakeup_time, early))
		            early_wakeup_time = early;
	        } else
	    	    early_wakeup_time = early;
	    } else {
		    if (time_add(early_wakeup_time, early_wakeup_advance) == orig_time)
		        time_early_wakeup_set_next(early_wakeup_time);
	    }
	}
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

	if (early_wakeup_fn && TIME_VALID(early_wakeup_time)) {
		if (time_ge(now, early_wakeup_time)) {
			time_early_wakeup_set_next(now+1);
		    early_wakeup_fn();
		}
	}

	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		uint32_t event_time = time_event_time[i];
		if (!TIME_VALID(event_time))
			continue;
		if (time_ge(now, event_time)) {
			time_event_time[i] = TIME_INVALID;
			time_event_fns[i]();
		}
	}
}

uint32_t time_to_next_event_and_wake(uint32_t *wake_time_p, uint32_t now)
{
	uint32_t remaining = 0xffffffff;
	uint32_t wake_time = now;
	int i;

	for (i = 0; i < ARRAY_SIZE(time_event_time); i++) {
		uint32_t event_time = time_event_time[i];
		uint32_t delta;
		if (!TIME_VALID(event_time))
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
	if (wake_time_p)
		*wake_time_p = wake_time;
	return remaining;
}

uint32_t time_to_next_event(void)
{
	return time_to_next_event_and_wake(NULL, time_now());
}

bool time_prepare_sleep(void)
{
	uint32_t now = time_now();
	uint32_t wake_time = now;
    uint32_t remaining = time_to_next_event_and_wake(&wake_time, now);

    if (!TIME_VALID(remaining))
		return true; // No plans to wake up, ever.

    /* If we had no wakeup events, we shouldn't have had an early wakeup
     * event. Let's check for early wakeup events now.
     */
    if (early_wakeup_fn && TIME_VALID(early_wakeup_time)) {
    	if (time_ge(wake_time, early_wakeup_time)) {
    		if (time_ge(now, early_wakeup_time))
    			return false; // No sleep, we have an event pending
    		remaining = time_sub(early_wakeup_time, now);
    		wake_time = early_wakeup_time;
    	}
    }

	if (remaining < TIME_SLEEP_TRHESHOLD)
		return false; // We need to wake up soon anyway.

	RTC_CompareSet(0, wake_time);

	return true;
}
