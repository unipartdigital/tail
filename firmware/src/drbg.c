/* drbg.c */

/* A DRGB. It's suitable for generating pseudo-random numbers, but should not
   be used for key material.
*/
#include <string.h>

#include "em_aes.h"

#include "aes.h"
#include "drbg.h"
#include "entropy.h"
#include "util.h"

/* These uses the AES hardware, but is only used internally by DRBG.
   Do not use them for encryption/authentication/anything else!
   Note that they are (and must be) zero-initialized.
*/
uint8_t drbg_key[16];
uint8_t drbg_vector[16];
uint8_t drbg_generated[16]; /* most recently generated value */
int32_t drbg_samples;
int32_t drbg_samples_required;

void drbg_init(void) {
    //int32_t entropy_per_sample = get_entropy_per_sample();
    //drbg_samples_required = max(512 / entropy_per_sample, 1024);
    drbg_samples_required = 1024; /*  FIXME once there's an entropy source*/
}

/* Note that this is intentionally ignoring a difference in byte order
   to maximize the number of bits of carry we get for free.
   In short, it's not adding 1, despite how it looks at a glance.
   It's also not strictly an increase, as it occasionally wraps.
*/
void increase_vector(uint8_t *vector) {
    uint64_t * vector_lens = (uint64_t *) vector;

    *(vector_lens + 1) = (int64_t) (*(vector_lens + 1) + 1);
}

void drbg_update(uint8_t *data) {
    uint8_t new_key[16];

    increase_vector(drbg_vector);
    aes_init();
    AES_ECB128(new_key, drbg_vector, 1, drbg_key, 1);
    xor128(new_key, data);

    increase_vector(drbg_vector);
    AES_ECB128(drbg_vector, drbg_vector, 1, drbg_key, 1);
    aes_deinit();
    memcpy(drbg_key, new_key, 16);

    if (drbg_samples < drbg_samples_required)
        drbg_samples++;
}

uint8_t *drbg_generate(void) {
    if (!drbg_ready())
        return NULL;
    increase_vector(drbg_vector);
    AES_ECB128(drbg_generated, drbg_vector, 1, drbg_key, 1);
    return drbg_generated;
}

bool drbg_ready(void) {
    return drbg_samples >= drbg_samples_required;
}

/* FIXME: this must stir in entropy when that is available.*/
void drbg_make_ready(uint8_t *data) {
    while (!drbg_ready())
        drbg_update(data);
}

void drbg_error(void) {
    drbg_samples = 0;
}
