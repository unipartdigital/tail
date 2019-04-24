/* aes_cmac_test.c: test that cmac operations work */

#include <stdbool.h>
#include <stdint.h>

#include "aes_cmac.h"
#include "aes_x86.h"
#include "util.h"
#include "x86_util.h"

/* 0 = test passed, other value = test failed */

/* test vectors from https://tools.ietf.org/html/rfc4493 */

void test_subkey(void) {
    uint8_t key[16];
    uint8_t aes_128_in[16];
    uint8_t aes_128_out[16];
    uint8_t aes_128_expected[16];
    uint8_t k1[16];
    uint8_t k2[16];
    uint8_t k1_expected[16];
    uint8_t k2_expected[16];

    set16bytes(key,              0x2b7e151628aed2a6, 0xabf7158809cf4f3c);
    set16bytes(aes_128_in,       0, 0);
    set16bytes(aes_128_out,      0, 0);
    set16bytes(aes_128_expected, 0x7df76b0c1ab899b3, 0x3e42f047b91b546f);
    set16bytes(k1,               0, 0);
    set16bytes(k2,               0, 0);
    set16bytes(k1_expected,      0xfbeed61835713366, 0x7c85e08f7236a8de);
    set16bytes(k2_expected,      0xf7ddac306ae266cc, 0xf90bc11ee46d513b);

    aes_ecb128(aes_128_out, aes_128_in, 16, key, true);
    check_aes_test(aes_128_out, aes_128_expected, 1);

    generate_subkey(k1, k2, key);
    check_aes_test(k1, k1_expected, 1);
    check_aes_test(k2, k2_expected, 1);
}

void test_cmac_empty(void) {
    uint8_t cmac[16];
    uint8_t expected[16];
    uint8_t key[16];

    set16bytes(key,      0x2b7e151628aed2a6, 0xabf7158809cf4f3c);
    set16bytes(expected, 0xbb1d6929e9593728, 0x7fa37d129b756746);
    aes_cmac(cmac, NULL, 0, key);
    check_aes_test(cmac, expected, 1);
}

void test_cmac16(void) {
    uint8_t cmac[16];
    uint8_t msg[16];
    uint8_t expected[16];
    uint8_t key[16];

    set16bytes(key,      0x2b7e151628aed2a6, 0xabf7158809cf4f3c);
    set16bytes(msg,      0x6bc1bee22e409f96, 0xe93d7e117393172a);
    set16bytes(expected, 0x070a16b46b4d4144, 0xf79bdd9dd04a287c);
    aes_cmac(cmac, msg, 16, key);
    check_aes_test(cmac, expected, 1);
}

void test_cmac40(void) {
    uint8_t cmac[16];
    uint8_t msg[40];
    uint8_t expected[16];
    uint8_t key[16];

    set16bytes(key,      0x2b7e151628aed2a6, 0xabf7158809cf4f3c);
    set16bytes(msg,      0x6bc1bee22e409f96, 0xe93d7e117393172a);
    set16bytes(msg+16,   0xae2d8a571e03ac9c, 0x9eb76fac45af8e51);
    set8bytes(msg+32,    0x30c81c46a35ce411);
    set16bytes(expected, 0xdfa66747de9ae630, 0x30ca32611497c827);
    aes_cmac(cmac, msg, 40, key);
    check_aes_test(cmac, expected, 1);
}

void test_cmac64(void) {
    uint8_t cmac[16];
    uint8_t msg[64];
    uint8_t expected[16];
    uint8_t key[16];

    set16bytes(key,      0x2b7e151628aed2a6, 0xabf7158809cf4f3c);
    set16bytes(msg,      0x6bc1bee22e409f96, 0xe93d7e117393172a);
    set16bytes(msg+16,   0xae2d8a571e03ac9c, 0x9eb76fac45af8e51);
    set16bytes(msg+32,   0x30c81c46a35ce411, 0xe5fbc1191a0a52ef);
    set16bytes(msg+48,   0xf69f2445df4f9b17, 0xad2b417be66c3710);
    set16bytes(expected, 0x51f0bebf7e3b9d92, 0xfc49741779363cfe);
    aes_cmac(cmac, msg, 64, key);
    check_aes_test(cmac, expected, 1);
}
