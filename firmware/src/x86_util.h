/* x86_util.h */

#ifndef _x86_UTIL_H
#define _x86_UTIL_H

void check_aes_test(uint8_t *out,uint8_t *expected,int blocks);
void show_mem_dbg(uint8_t *base,int n);
void write_hex(uint8_t val);
void write_string(char *str);
#endif /* _x86_UTIL_H */
