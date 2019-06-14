#include "lfsr.h"

#define LFSR_POLYNOMIAL 0x80200003

int32_t lfsr_state = 0;

void seed_lfsr(int32_t seed)
{
    lfsr_state = seed;
}

int32_t lfsr(void)
{
    bool lsb = lfsr_state & 1;
    lfsr_state >>= 1;
    if (lsb)
        lfsr_state ^= LFSR_POLYNOMIAL;

    return lfsr_state;
}
