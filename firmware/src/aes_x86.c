/* aes_x86.c */
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#include <openssl/aes.h>

void key_to_aeskey(AES_KEY *aes_key, const uint8_t *in_key) {
    AES_set_encrypt_key((const unsigned char *) in_key, 128, aes_key);
}

/* Note that the 'key' argument needs to be a decryption key for decryption.
   This can be retrieved from an encryption key with AES_DecryptKey128. */
void aes_cbc128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                const uint8_t *iv,
                bool encrypt) {

    AES_KEY *aes_key = malloc(sizeof(AES_KEY));
    key_to_aeskey(aes_key, key);

    AES_cbc_encrypt((const unsigned char *) in, (unsigned char *) out,
                    (size_t) len, aes_key,
                    (unsigned char *) iv, (const int) encrypt);
    free(aes_key);
}

/* Note that the 'key' argument needs to be a decryption key for decryption.
   This can be retrieved from an encryption key with AES_DecryptKey128. */
void aes_ecb128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                bool encrypt) {

    AES_KEY *aes_key = malloc(sizeof(AES_KEY));
    key_to_aeskey(aes_key, key);

    for (int i = 0; i < len; i += 16) {
        AES_ecb_encrypt((const unsigned char *) in + i * 16,
                        (unsigned char *) out + i * 16,
                        aes_key, (const int) encrypt);
    }
    free(aes_key);
}
