/* entropy.h */
#ifndef _ENTROPY_H
#define _ENTROPY_H

#include <stdbool.h>
#include <stdint.h>

int32_t entropy_per_sample(void);
int32_t entropy_samples_til_ready(void);
void entropy_register(uint32_t);
void entropy_poll(void);
#endif /* _ENTROPY_H */
