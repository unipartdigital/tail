/* drbg.c */

/* A DRGB. It's suitable for generating pseudo-random numbers, but should not
   be used for key material.
*/
#include <string.h>

#include "em_aes.h"

#include "aes.h"
#include "drbg.h"
#include "entropy.h"
#include "uart.h"

/* These uses the AES hardware, but is only used internally by DRBG.
   Do not use them for encryption/authentication/anything else!
   Note that they are (and must be) zero-initialized.
*/
uint8_t drbg_key[16];
uint8_t drbg_vector[16];
uint8_t drbg_generated[16]; /* most recently generated value */
int32_t drbg_samples;
int32_t drbg_samples_required;

/* Initialize the drbg. Only drbg_samples_required absolutely has to be set,
   but setting the other values allows for deterministic re-initialization.
   The values for drbg_key and drbg_vector are deterministic, but not magical;
   they could be anything. */
void drbg_init(void) {
    drbg_samples = 0;
    drbg_samples_required = entropy_samples_til_ready();
    memset(drbg_key, 0xaa, 16);
    memset(drbg_vector, 0x99, 16);
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

/* Note that there are only a few bits of entropy per entropy sample.
   This is not a 'full' entropy source - there are about 4-7 bits of entropy
   per sample, not 64! */
void drbg_update(uint32_t entropy_sample) {
    uint32_t new_key[4];

    increase_vector(drbg_vector);
    aes_init();
    AES_ECB128((uint8_t *)new_key, drbg_vector, 16, drbg_key, 1);
    /* Xor with the lowest chunk of the key the size of the entropy sample */
    new_key[3] ^= entropy_sample;

    increase_vector(drbg_vector);
    AES_ECB128(drbg_vector, drbg_vector, 16, drbg_key, 1);
    aes_deinit();
    memcpy(drbg_key, new_key, 16);

    if (drbg_samples < drbg_samples_required)
        drbg_samples++;
}

const uint8_t *drbg_generate(void) {
    if (!drbg_ready())
        return NULL;
    increase_vector(drbg_vector);
    aes_ecb128(drbg_generated, drbg_vector, 16, drbg_key, 1);
    return drbg_generated;
}

bool drbg_ready(void) {
    /* If drbg_ready is called before drbg_init, it definitely is not ready. */
    if (!drbg_samples_required)
        return 0;
    return drbg_samples >= drbg_samples_required;
}

void drbg_error(void) {
    drbg_samples = 0;
}
