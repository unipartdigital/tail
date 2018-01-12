/* time.h */

#ifndef _TIME_H
#define _TIME_H

#include <stdint.h>
#include <stdbool.h>
#include "em_rtc.h"

/* Don't go to sleep less than this amount of time before an event */
#define TIME_SLEEP_TRHESHOLD TIME_FROM_MS(100)


/* We're using the 32.768kHz RCO */
#define TIME_CLOCK 32768

/* We choose this value carefully to trade off between maximum sleep time
 * and resolution. The choice of 256 gives us a time resolution of 7.81ms
 * and a timer overflow of 1.52 days. This means we can sleep for up to
 * 0.76 days.
 */
#define TIME_PRESCALER 256

#define TIME_TO_SECONDS(x)   (((x) * TIME_PRESCALER) / TIME_CLOCK)
#define TIME_TO_MS(x)        (((x) * TIME_PRESCALER * 1000) / TIME_CLOCK)
#define TIME_FROM_SECONDS(x) (((x) * TIME_CLOCK) / TIME_PRESCALER)
#define TIME_FROM_MS(x)      (((x) * TIME_CLOCK) / (TIME_PRESCALER * 1000))

#define TIME_INVALID 0xffffffff

/* Here we list all the events which can be scheduled. Each one corresponds
 * to a function of the same name, which you must declare. That is what will
 * be called when the timer expires.
 */
#define TIME_EVENTS \
	X(tag_start) \
	X(range_start)

#define X(x) time_event_id_##x,
typedef enum {
	TIME_EVENTS
} time_event_id;
#undef X

#define X(x) void x(void);
TIME_EVENTS
#undef X

typedef void (*time_event_fn)(void);

void time_init(void);
uint32_t time_now(void);
/* True if a >= b */
bool time_ge(uint32_t a, uint32_t b);
uint32_t time_add(uint32_t a, uint32_t b);
uint32_t time_sub(uint32_t a, uint32_t b);
void time_event_schedule_at(time_event_id index, uint32_t time);
void time_event_schedule_in(time_event_id index, uint32_t time);

#define time_event_at(event, time) time_event_schedule_at(time_event_id_##event, time)
#define time_event_in(event, time) time_event_schedule_in(time_event_id_##event, time)
#define time_event_clear(event)    time_event_schedule_at(time_event_id_##event, TIME_INVALID)

void time_event_poll(void);
/* Returns true if it's OK to sleep. */
bool time_prepare_sleep(void);

#endif
