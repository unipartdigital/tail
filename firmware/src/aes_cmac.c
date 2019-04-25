#include <string.h>
#include <stdint.h>

#include "aes_x86.h"
#include "util.h"

void generate_subkey(uint8_t *k1, uint8_t *k2, const uint8_t *k) {
    uint8_t const_zero[16];
    uint8_t const_rb[16];
    int key_msb;

    set16bytes(const_zero, 0, 0);
    set16bytes(const_rb,   0, 0x87);
    aes_ecb128(k1, const_zero, 16, k, true);

    key_msb = msb(k1);
    lshift128(k1, 1);
    if (key_msb) {
        xor128(k1, const_rb);
    }

    memcpy(k2, k1, 16);
    key_msb = msb(k2);
    lshift128(k2, 1);
    if (key_msb) {
        xor128(k2, const_rb);
    }
}


void aes128_pad(uint8_t *m_last, int rlast) {
    m_last[rlast] = 0x80;
    for (int i = rlast + 1; i < 16; i++) {
        m_last[i] = 0;
    }
}

void aes_cmac(uint8_t *cmac, uint8_t *msg, uint32_t len, uint8_t *key) {
    const int bsize = 16;
    uint8_t const_zero[16];
    uint8_t x[16];
    uint8_t y[16];
    uint8_t k1[16];
    uint8_t k2[16];
    uint8_t m_last[16];
    int nblocks;
    int rlast = len % bsize;
    int last_block_complete;

    set16bytes(const_zero, 0, 0);
    generate_subkey(k1, k2, key);

    nblocks = (len + bsize - 1) / bsize;

    if (nblocks == 0) {
        nblocks = 1;
        last_block_complete = false;
    } else {
        if ((len % bsize == 0)) {
            last_block_complete = true;
        } else {
            last_block_complete = false;
        }
    }

    if (last_block_complete) {
        //M_last := M_n XOR K1;
        memcpy(m_last, msg + (nblocks - 1) * bsize, bsize);
        xor128(m_last, k1);
    } else {
        // M_last := padding(M_n) XOR K2;
        memcpy(m_last, const_zero, bsize);
        if (msg) {
            memcpy(m_last, msg + (nblocks - 1) * bsize, rlast);
        }
        aes128_pad(m_last, rlast);
        xor128(m_last, k2);
    }

    memcpy(x, const_zero, bsize);
    for (int i = 0; i < nblocks - 1; i++) {
        memcpy(y, x, bsize);
        xor128(y, msg + i * bsize);
        /*printf("\nafter xor\n");
        show_mem_dbg(y, 16);
        show_mem_dbg(x, 16);
        show_mem_dbg(key, 16);*/
        aes_ecb128(x, y, bsize, key, true);
        //printf("after AES\n");
        //show_mem_dbg(x, 16);
    }

    memcpy(y, m_last, bsize);
    xor128(y, x);
    aes_ecb128(cmac, y, bsize, key, true);
}

