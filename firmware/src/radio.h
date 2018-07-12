/* radio.h */

#ifndef _RADIO_H
#define _RADIO_H

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    uint8_t chan;
    bool prf_high; /* false = 16MHz, true = 64MHz */
    uint8_t tx_plen; /* Preamble length */
    uint8_t rx_pac;
    uint8_t tx_pcode;
    uint8_t rx_pcode;
    bool ns_sfd;
    uint8_t data_rate;
    bool long_frames;
    uint16_t sfd_timeout;
} radio_config_t;

#define RADIO_RATE_110K    0
#define RADIO_RATE_850K    1
#define RADIO_RATE_6M8     2

/* Preamble Acquisition Chunk (PAC) Size in symbols */
#define RADIO_PAC_8        0   /* recommended for RX of preamble length 128 and below */
#define RADIO_PAC_16       1   /* recommended for RX of preamble length 256 */
#define RADIO_PAC_32       2   /* recommended for RX of preamble length 512 */
#define RADIO_PAC_64       3   /* recommended for RX of preamble length 1024 and up */

/* TX Preamble length in symbols */
#define RADIO_PLEN_4096   12
#define RADIO_PLEN_2048   10 /* Non-standard */
#define RADIO_PLEN_1536    9 /* Non-standard */
#define RADIO_PLEN_1024    8
#define RADIO_PLEN_512     7 /* Non-standard */
#define RADIO_PLEN_256     6 /* Non-standard */
#define RADIO_PLEN_128     5 /* Non-standard */
#define RADIO_PLEN_64      4

#define RADIO_SFD_TIMEOUT_DEFAULT 0x1041

/* To be used in the first argument of radio_configsleep */
#define RADIO_SLEEP_PRESERVE   0x100
#define RADIO_SLEEP_LOADOPSET   0x80
#define RADIO_SLEEP_CONFIG      0x40
#define RADIO_SLEEP_LOADEUI     0x08
#define RADIO_SLEEP_GOTORX      0x04
#define RADIO_SLEEP_TANDV       0x01

/* To be used in the second argument of radio_configsleep */
#define RADIO_SLEEP_XTAL_ENABLE 0x10
#define RADIO_SLEEP_WAKE_CONUT  0x08
#define RADIO_SLEEP_WAKE_CS     0x04
#define RADIO_SLEEP_WAKE_WAKEUP 0x02
#define RADIO_SLEEP_ENABLE      0x01

typedef void (*radio_callback)(void);

typedef struct radio_callbacks {
	radio_callback txdone;
	radio_callback rxdone;
	radio_callback rxerror;
	radio_callback rxtimeout;
} radio_callbacks;

void radio_init(bool loadlde);
void radio_configure(radio_config_t *config);
bool radio_writepayload(uint8_t *data, uint16_t len, uint16_t offset);
void radio_txprepare(uint16_t len, uint16_t offset, bool ranging);
bool radio_txstart(bool delayed);
bool radio_rxstart(bool delayed);

// void radio_spiheader(uint8_t file, uint16_t reg, bool write);
void radio_read(uint8_t file, uint16_t reg, uint8_t *data, uint8_t len);
void radio_write(uint8_t file, uint16_t reg, uint8_t *data, uint8_t len);
uint8_t radio_read8(uint8_t file, uint16_t reg);
void radio_write8(uint8_t file, uint16_t reg, uint8_t data);
uint16_t radio_read16(uint8_t file, uint16_t reg);
void radio_write16(uint8_t file, uint16_t reg, uint16_t data);
uint32_t radio_read32(uint8_t file, uint16_t reg);
void radio_write32(uint8_t file, uint16_t reg, uint32_t data);
void radio_txpacket(uint8_t *data, int len);
bool radio_rxpacket(void *data, int maxlen);
void radio_txrxoff(void);
void radio_loadlde(void);
void radio_setclocks(int clocks);
void radio_rxreset(void);
void radio_softreset(void);
uint32_t radio_deviceid(void);
void radio_aonarrayupload(void);
void radio_aonconfigupload(void);
void delay(int ms);
void radio_setcallbacks(radio_callbacks *callbacks);
int radio_getpayload(void *data, int maxlen);
void radio_setrxtimeout(uint16_t time);
void radio_setstarttime(uint32_t time);
void radio_readtxtimestamp(uint8_t *time);
void radio_readrxtimestamp(uint8_t *time);
void radio_antenna_delay_rx(uint16_t delay);
void radio_antenna_delay_tx(uint16_t delay);
void radio_xtal_trim(uint8_t value);
uint32_t radio_otp_read32(uint32_t address);
void radio_configsleep(uint16_t mode, uint8_t wake);
void radio_entersleep(void);
void radio_wakeup(void);
void radio_cswakeup(void);
void radio_wakeup_action(void);
void radio_cswakeup_action(void);
void radio_leds(bool on, int time);
void radio_leds_restore(void);

#endif /* _RADIO_H */
