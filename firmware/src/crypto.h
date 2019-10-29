/* crypto.h */
#ifndef _CRYPTO_H
#define _CRYPTO_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "drbg.h"

#define CRYPTO_KDF_CBC 1 /* Derive CBC encryption key from tag key */
#define CRYPTO_KDF_CMAC 2 /* Derive CMAC authentication key from tag key */
/* Deriving the tag key from the master key is not possible on a tag */
#define CRYPTO_KDF_IV 4 /* Derive key to turn cookie into an IV from tag key */

void crypto_init(void);
bool crypto_update_cookie(void);
bool crypto_get_cookie(uint8_t *cookie_buf);
bool crypto_kdf(uint8_t *derived_key, uint8_t op);
bool derive_iv_from_cookie(uint8_t *iv, uint8_t *cookie);
#endif /* _CRYPTO_H */
