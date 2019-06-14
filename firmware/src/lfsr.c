#include "lfsr.h"

#define LFSR_POLYNOMIAL 0x80200003

uint32_t lfsr_state;

void lfsr_seed(uint32_t seed)
{
    lfsr_state = seed;
}

uint32_t lfsr(void)
{
    bool lsb = lfsr_state & 1;
    lfsr_state >>= 1;
    if (lsb)
        lfsr_state ^= LFSR_POLYNOMIAL;

    return lfsr_state;
}
