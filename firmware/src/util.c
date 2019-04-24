/* util.c: provide basic utilities shared across platforms for production use */

#include <stdint.h>

void letobe64(uint64_t *le64bits) {
    uint8_t tmp;
    uint8_t *bits = (uint8_t *) le64bits;
    for (int i = 0; i < 4; i++) {
        tmp = bits[i];
        bits[i] = bits[7 - i];
        bits[7 - i] = tmp;
    }
}

void set8bytes_be(uint8_t *buf, uint64_t in) {
    int i;
    uint8_t *in_b = (uint8_t *) &in;

    for (i = 0; i < 8; i++) {
        buf[i] = in_b[i];
    }
}

void set8bytes(uint8_t *buf, uint64_t in) {
    int i;
    uint8_t *in_b = (uint8_t *) &in;

    for (i = 0; i < 8; i++) {
        buf[i] = in_b[7 - i];
    }
}

void set16bytes(uint8_t *buf, uint64_t in0, uint64_t in1) {
    set8bytes(buf, in0);
    set8bytes(buf + 8, in1);
}

int msb(uint8_t *buf) {
    return (buf[0] & 0x80) == 0x80;
}

/* in-place left shift for 128 bit big endian buffer */
void lshift128(uint8_t *buf, uint8_t n) {
    uint64_t *t;
    while (n--) {
        t = (uint64_t *) buf;
        letobe64(t);
        set8bytes(buf, *t << 1);
        buf[7] += msb(buf + 8);
        t = (uint64_t *) (buf + 8);
        letobe64(t);
        set8bytes(buf + 8, *t << 1);
    }
}

/* in-place xor for 128 bit buffer; overwrites first argument */
void xor128(uint8_t *a_out, uint8_t *b) {
    uint64_t *out;
    uint64_t *b64;
    uint64_t tmp;

    out = (uint64_t *) a_out;
    b64 = (uint64_t *) b;
    tmp = (*out) ^ (*b64);
    set8bytes_be(a_out, tmp);

    out = (uint64_t *) (a_out + 8);
    b64 = (uint64_t *) (b + 8);
    tmp = (*out) ^ (*b64);
    set8bytes_be(a_out + 8, tmp);
}
