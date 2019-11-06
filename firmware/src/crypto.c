/* crypto.c */

#include "stdint.h"

#include "aes_cmac.h"
#include "config.h"
#include "crypto.h"

uint8_t crypto_cookie[16]        __attribute__((aligned(4)));
uint8_t crypto_tag_key[16]       __attribute__((aligned(4)));
uint8_t crypto_iv_cookie_key[16] __attribute__((aligned(4)));
bool crypto_has_tag_key = 0;
bool crypto_cookie_ready = 0;

void crypto_init() {
    int key_bytes = config_get(config_key_tag_key, crypto_tag_key, 16);
    if (key_bytes != 16) {
        return;
    } else {
        crypto_has_tag_key = 1;
    }
    drbg_init();
    crypto_update_cookie();
    crypto_kdf(crypto_iv_cookie_key, CRYPTO_KDF_IV);
}

/* This also handles initialization */
bool crypto_update_cookie() {
    const uint8_t *cookie;

    if ((!crypto_has_tag_key) || (!drbg_ready())) {
        memset(crypto_cookie, 0, 16);
        crypto_cookie_ready = 0;
        return 0;
    }

    cookie = drbg_generate();
    memcpy(crypto_cookie, cookie, 16);
    crypto_cookie_ready = 1;
    return 1;
}

bool crypto_get_cookie(uint8_t *cookie_buf) {
    if (!crypto_has_tag_key) {
        return 0;
    }
    if (!crypto_cookie_ready) {
        crypto_update_cookie();
        if (!crypto_cookie_ready)
            return 0;
    }

    memcpy(cookie_buf, crypto_cookie, 16);
    return 1;
}


/* Derive a crypto key from the tag key, storing it in derived_key. This must
   have space for a 128-bit value.
   Explanation of the contents of kdf_string is at
   https://wiki.unipart.io/wiki/Tail_tag_protocol#Key_derivation.

   This function explicitly calls config_get, which can take unbounded time.
   This is acceptable, as it is extremely rarely called. (At the time of
   writing, it is called once during crypto initialiazation. If it is called
   more often in the future, consider refactoring.)
 */
bool crypto_kdf(uint8_t *derived_key, uint8_t op) {
    uint8_t kdf_string[13];
    uint8_t eui[13];
    if (!crypto_has_tag_key) {
        return 0;
    }

    int eui_bytes = config_get(config_key_eui, eui, 8);
    if (eui_bytes != 8) {
        return 0;
    }

    kdf_string[0] = op;
    kdf_string[1] = 0x38;
    kdf_string[2] = 0;
    memcpy(kdf_string+3, eui, 8);
    kdf_string[11] = 128;
    kdf_string[12] = 0;

    aes_cmac(derived_key, kdf_string, 13, crypto_tag_key);
    return 1;
}

/* IV (16 bytes) is only used as for the output of the function.
   The cookie is also 16 bytes. */
bool derive_iv_from_cookie(uint8_t *iv, uint8_t *cookie) {
    if (!crypto_has_tag_key) {
        return 0;
    }
    aes_cmac(iv, cookie, 16, crypto_iv_cookie_key);
    return 1;
}
