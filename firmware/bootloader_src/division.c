unsigned __aeabi_uidiv(unsigned numerator, unsigned denominator)
{
    /* Ignore division by 0 */
    unsigned quotient = 0;
    unsigned remainder = 0;
    for (unsigned bit = 0x80000000; bit != 0; bit >>= 1) {
        remainder = remainder << 1;
        if (numerator & bit) {
            remainder = remainder - denominator;
            quotient |= bit;
        }
    }
    return quotient;
}
