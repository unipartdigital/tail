/* entropy.h */
#ifndef _ENTROPY_H
#define _ENTROPY_H

#include <stdbool.h>
#include <stdint.h>

int32_t entropy_per_sample(void);
int32_t entropy_failure_detect_samples(void);
void entropy_starttime(uint64_t);
void entropy_register(uint64_t);
void entropy_poll(void);
#endif /* _ENTROPY_H */