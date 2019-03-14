/* byteorder.h */

#define htons(x) bswap16(x)
#define ntohs(x) bswap16(x)

#define htonl(x) bswap32(x)
#define ntohl(x) bswap32(x)

#ifndef bswap16
#define bswap16(x) (((x) >> 8) | ((x) << 8))
#endif

#ifndef bswap32
#define bswap32(x) ((bswap16((x) >> 16)) | (bswap16((x) & 0xffff) << 16))
#endif

/* swap byte order of bit index into 16 bit quantity */
#define bitoffset16(x) (((x)>7)?((x)-8):(x))

