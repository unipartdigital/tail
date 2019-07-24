/* event.c */

#include <stdint.h>

volatile uint32_t event_mask;

void event_log(int event)
{
    event_mask |= (1<<event);
}

uint32_t event_get(void)
{
    return event_mask;
}

void event_clear(void)
{
    event_mask = 0;
}

