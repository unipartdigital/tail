/* event.h */

#ifndef _EVENT_H
#define _EVENT_H

#include <stdint.h>

#define EVENT_TIME_TOO_OLD   0
#define EVENT_BATTERY_FLAT   1
#define EVENT_ALREADY_ACTIVE 2

void event_log(int event);
uint32_t event_get(void);
void event_clear(void);

#endif /* _EVENT_H */
