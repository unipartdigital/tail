/* aes.h */

#ifndef _AES_H
#define _AES_H

#include "em_aes.h"
#include "em_cmu.h"

void aes_init(void);

void aes_deinit(void);

void aes_decrypt_key128(uint8_t *out, const uint8_t *in);

void aes_cbc128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                const uint8_t *iv,
                bool encrypt);

void aes_cbc128_encdecrypt(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                const uint8_t *iv);


void aes_ecb128(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key,
                bool encrypt);

void aes_ecb128_encdecrypt(uint8_t *out,
                const uint8_t *in,
                unsigned int len,
                const uint8_t *key);

#endif /* _AES_H */
