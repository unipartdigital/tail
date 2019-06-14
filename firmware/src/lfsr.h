/* lfsr.h */

#ifndef _LFSR_H
#define _LFSR_H
#include <stdbool.h>
#include <stdint.h>

void lfsr_seed(uint32_t seed);
uint32_t lfsr(void);
#endif /* _LFSR_H */
