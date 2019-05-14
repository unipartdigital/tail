#include "misc.h"

void delay(int ms)
{
    int i;
    volatile int count;
    /* XXX calibrate this */
    for (i = 0; i < ms; i++)
        for (count = 0; count < 1000; count++) ;
}
