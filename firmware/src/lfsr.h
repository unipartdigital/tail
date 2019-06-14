/* lfsr.h */

#ifndef _LFSR_H
#define _LFSR_H
#include <stdbool.h>
#include <stdint.h>

void seed_lfsr(int32_t seed);
int32_t lfsr(void);
#endif /* _LFSR_H */
