/* x86_util.c: provide basic utilities for tests on x86 */

#include <string.h>
#include <stdint.h>
#include <stdio.h>

#include "util.h"

void write_string(char *str) {
    printf("%s", str);
}

void write_hex(uint8_t val) {
    printf("%02x", val);
}

void show_mem_dbg(uint8_t *base, int n) {
    int i, t;
    for (i = 0; i < n; i++) {
        t = (uint32_t) base[i];
        write_hex(t);
        write_string(" ");
    }
    write_string("\r\n");
}

void check_aes_test(uint8_t *out, uint8_t *expected, int blocks) {
    int eq = memcmp(out, expected, blocks * 16);
    if (eq == 0) {
        write_string("equal, crypto test passed!\r\n");
    } else {
        write_string("not equal, crypto test failed!\r\n");
        show_mem_dbg(out, blocks * 16);
    }
}

