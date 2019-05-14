/* timer.h */

#ifndef _TIMER_H
#define _TIMER_H

#include <stdint.h>
#include <stdbool.h>

void timer_init(void);
void timer_sethandler(void (*fn)(void));
void timer_deinit(void);
uint32_t timer_frequency(void);
void timer_set(uint32_t delay);
void timer_start(void);
void timer_stop(void);
bool timer_prepare_sleep(void);

#endif /* _TIMER_H */
