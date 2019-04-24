/* aes.c */

/* Use the AES hardware on the chip.
   Note that all of these wrapper functions take care of turning the hardware
   on and off.
*/

#include "aes.h"

void aes_init(void) {
    CMU_ClockEnable(cmuClock_AES, true);
}

void aes_deinit(void) {
    CMU_ClockEnable(cmuClock_AES, false);
}

void aes_decrypt_key128(uint8_t *out, const uint8_t *in) {
    aes_init();
    AES_DecryptKey128(out, in);
    aes_deinit();
}

/* Note that the 'key' argument needs to be a decryption key for decryption.
   This can be retrieved from an encryption key with AES_DecryptKey128. */
void aes_cbc128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                const uint8_t *iv,
                bool encrypt) {
    aes_init();
    AES_CBC128(out, in, len, key, iv, encrypt);
    aes_deinit();
}

/* Do AES CBC 128 decryption, given the encryption key */
void aes_cbc128_encdecrypt(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                const uint8_t *iv) {
    uint8_t decryption_key[16];
    aes_init();
    AES_DecryptKey128(decryption_key, key);
    AES_CBC128(out, in, len, decryption_key, iv, false);
    aes_deinit();
}

/* Note that the 'key' argument needs to be a decryption key for decryption.
   This can be retrieved from an encryption key with AES_DecryptKey128. */
void aes_ecb128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                bool encrypt) {
    aes_init();
    AES_ECB128(out, in, len, key, encrypt);
    aes_deinit();
}

/* Do AES ECB 128 decryption, given the encryption key */
void aes_ecb128_encdecrypt(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key) {
    uint8_t decryption_key[16];
    aes_init();
    AES_DecryptKey128(decryption_key, key);
    AES_ECB128(out, in, len, decryption_key, false);
    aes_deinit();
}
