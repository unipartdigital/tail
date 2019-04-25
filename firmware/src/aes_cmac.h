/* aes_cmac.h */

#ifndef _AES_CMAC_H
#define _AES_CMAC_H
void aes_cmac(uint8_t *cmac,uint8_t *msg,uint32_t len,uint8_t *key);
void aes128_pad(uint8_t *m_last,int rlast);
void generate_subkey(uint8_t *k1,uint8_t *k2,const uint8_t *k);
#endif /* _AES_CMAC_H */
