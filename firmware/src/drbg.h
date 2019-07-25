/* drbg.h */
#ifndef _DRBG_H
#define _DRBG_H

#include <stdint.h>
#include <stdbool.h>

void drbg_error(void);
bool drbg_ready(void);
uint8_t *drbg_generate(void);
void drbg_update(uint32_t);
void increase_vector(uint8_t *);
void drbg_init(void);
#endif /* _DRBG_H */
