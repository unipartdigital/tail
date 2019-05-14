/* util.h */

#ifndef _UTIL_H
#define _UTIL_H
void xor128(uint8_t *a_out,uint8_t *b);
void lshift128(uint8_t *buf,uint8_t n);
int msb(uint8_t *buf);
void set16bytes(uint8_t *buf,uint64_t in0,uint64_t in1);
void set8bytes(uint8_t *buf,uint64_t in);
#endif /* _UTIL_H */
