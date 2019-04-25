/* aes_x86.h */

#ifndef _AES_X86_H
#define _AES_X86_H

#include <stdbool.h>
#include <stdint.h>
#include <openssl/aes.h>
void aes_cbc128(uint8_t *out,const uint8_t *in,unsigned int len,const uint8_t *key,const uint8_t *iv,bool encrypt);
void aes_ecb128(uint8_t *out,const uint8_t *in,unsigned int len,const uint8_t *key,bool encrypt);
void key_to_aeskey(AES_KEY *aes_key,const uint8_t *in_key);
#endif /* _AES_X86_H */
