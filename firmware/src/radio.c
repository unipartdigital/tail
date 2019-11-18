/* radio.c */

#include "radio_spi.h"
#include "radio_reg.h"
#include <stdbool.h>
#include "em_gpio.h"
#include "radio.h"

#define STATUS_RX_DONE          0x00002000
#define STATUS_RX_TIMEOUT       0x00020000
#define STATUS_RX_ERROR         0x04259000
#define STATUS_RX_DONE_CLEAR    0x00006f00   /* RXDFR RXFCG RXPRD RXSFDD RXPHD LDEDONE */
#define STATUS_RX_TIMEOUT_CLEAR 0x00020000
#define STATUS_RX_ERROR_CLEAR   0x24259000
#define STATUS_RX_ERROR_RESET   0x00031000 /* RXPHE, RXRFSL, RXRFTO */

/* For now */
#define STATUS_TX_DONE          0x00000080
#define STATUS_TX_CLEAR         0x000000f0

#define STATUS_ALL_CLEAR (STATUS_RX_DONE_CLEAR | STATUS_RX_ERROR_CLEAR | STATUS_TX_CLEAR)

#define STATUS_TX_ENABLE        STATUS_TX_DONE
#define STATUS_RX_ENABLE        (STATUS_RX_DONE | STATUS_RX_TIMEOUT | STATUS_RX_ERROR)

#undef RADIO_DEBUG

#ifdef RADIO_DEBUG
#define RADIO_DEBUG_SIZE 1024
uint8_t radio_debug_buf[RADIO_DEBUG_SIZE];
int radio_debug_ptr = 0;
# define radio_debug_write(x) do { \
	    radio_debug_buf[radio_debug_ptr++] = x; \
	    if (radio_debug_ptr >= RADIO_DEBUG_SIZE) \
		    radio_debug_ptr = 0; \
    } while (0)
#else
# define radio_debug_write(x) ((void) 0)
#endif

#define radio_spi_read() radio_spi_transfer(0)
#define radio_spi_write(x) radio_spi_transfer(x)
static inline uint8_t radio_spi_transfer(uint8_t data)
{
  // We only ever use this function to operate the spi interface,
  // so the TX buffer should always have space in it at this point.
//  while (!(USART0->STATUS & USART_STATUS_TXBL)) ;
  USART0->TXDATA = (uint32_t)data;
  while (!(USART0->STATUS & USART_STATUS_TXC)) ;
  return (uint8_t)USART0->RXDATA;
}

static inline void radio_spi_read_burst(uint8_t *data, int len)
{
	int i;
	USART0->TXDATA = 0;
	for (i = 0; i < len-1; i++) {
		while (!(USART0->STATUS & USART_STATUS_TXC)) ;
		USART0->TXDATA = 0;
		data[i] = (uint8_t)USART0->RXDATA;
	}
	while (!(USART0->STATUS & USART_STATUS_TXC));
	data[i] = (uint8_t)USART0->RXDATA;
}

static inline void radio_spi_write_burst(uint8_t *data, int len)
{
#if 1
	int i;
	USART0->TXDATA = (uint32_t)data[0];
	for (i = 1; i < len; i++) {
		while (!(USART0->STATUS & USART_STATUS_TXC)) ;
		USART0->TXDATA = (uint32_t)data[i];
		(void)USART0->RXDATA;
	}
	while (!(USART0->STATUS & USART_STATUS_TXC));
	(void)USART0->RXDATA;
#else
	for (int i = 0; i < len; i++) {
	  USART0->TXDATA = (uint32_t)data[i];
	  while (!(USART0->STATUS & USART_STATUS_TXC)) ;
	  (void)USART0->RXDATA;
	}
#endif
}

#if 1

void (*radio_callback_txdone)(void)    = NULL;
void (*radio_callback_rxdone)(void)    = NULL;
void (*radio_callback_rxtimeout)(void) = NULL;
void (*radio_callback_rxerror)(void)   = NULL;

static uint32_t fs_pllcfg_values[] = {
		/* 1 */ 0x09000407,
		/* 2 */ 0x08400508,
		/* 3 */ 0x08401009,
		/* 4 */ 0x08400508,
		/* 5 */ 0x0800041D,
		/* 7 */ 0x0800041D
};

static uint8_t fs_plltune_values[] = {
		/* 1 */ 0x1E,
		/* 2 */ 0x26,
		/* 3 */ 0x56,
		/* 4 */ 0x26,
		/* 5 */ 0xBE,
		/* 7 */ 0xBE
};

static uint32_t rf_txctrl_values[] = {
		/* 1 */ 0x00005C40,
		/* 2 */ 0x00045CA0,
		/* 3 */ 0x00087CC0,
		/* 4 */ 0x00045C80,
		/* 5 */ 0x001E3FE0,
		/* 7 */ 0x001E7DE0
};

static uint16_t drx_tune0b_values[] = {
		/* 110K, standard SFD */     0x000A,
		/* 110K, non-standard SFD */ 0x0016,
		/* 850K, standard SFD */     0x0001,
		/* 850K, non-standard SFD */ 0x0006,
		/* 6M8,  standard SFD */     0x0001,
		/* 6M8,  non-standard SFD */ 0x0002
};

static uint32_t drx_tune2_values[] = {
		/* PAC  8, 16 MHz PRF */ 0x311A002D,
		/* PAC  8, 64 MHz PRF */ 0x313B006B,
		/* PAC 16, 16 MHz PRF */ 0x331A0052,
		/* PAC 16, 64 MHz PRF */ 0x333B00BE,
		/* PAC 32, 16 MHz PRF */ 0x351A009A,
		/* PAC 32, 64 MHz PRF */ 0x353B015E,
		/* PAC 64, 16 MHz PRF */ 0x371A011D,
		/* PAC 64, 64 MHz PRF */ 0x373B0296
};

static uint8_t sfd_length_values[] = {
		/* 110K */ 64,
		/* 850K */ 16,
		/* 6M8  */  8
};

static uint16_t repc_values[] = {
    /* 0 */ 0,
	/* 1 */ 0x5998,
	/* 2 */ 0x5998,
	/* 3 */ 0x51EA,
	/* 4 */ 0x428E,
	/* 5 */ 0x451E,
	/* 6 */ 0x2E14,
	/* 7 */ 0x8000,
	/* 8 */ 0x51EA,
	/* 9 */ 0x28F4,
	/* 10 */ 0x3332,
	/* 11 */ 0x3AE0,
	/* 12 */ 0x3D70,
	/* 13 */ 0x3AE0,
	/* 14 */ 0x35C2,
	/* 15 */ 0x2B84,
	/* 16 */ 0x35C2,
	/* 17 */ 0x3332,
	/* 18 */ 0x35C2,
	/* 19 */ 0x35C2,
	/* 20 */ 0x47AE,
	/* 21 */ 0x3AE0,
	/* 22 */ 0x3850,
	/* 23 */ 0x30A2,
	/* 24 */ 0x3850
};

static uint32_t radio_syscfg;
static bool radio_long_frames;
static uint32_t radio_tx_fctrl;
static uint8_t radio_trim_init;
static uint16_t radio_aon_wcfg;
static uint8_t radio_otp_rev;
static uint32_t radio_chipid;
static uint32_t radio_lotid;
static bool radio_ledstate;
static int radio_ledtime;
static uint8_t radio_fs_plltune;
static bool radio_prf_high;
static uint16_t radio_saved_antenna_delay_tx;
static bool radio_doublebuffer_enabled;

void delay(int ms)
{
    int i;
	volatile int count;
    /* XXX calibrate this */
	for (i = 0; i < ms; i++)
        for (count = 0; count < 1000; count++) ;
}

#define RADIO_IRQ_LINE 9

static inline bool radio_intoff(void)
{
	bool enabled = GPIO->IEN & (1<<RADIO_IRQ_LINE);
	if (enabled)
		GPIO->IEN &= ~(1<<RADIO_IRQ_LINE);
	return enabled;
}

static inline void radio_inton(bool enable)
{
	if (enable)
        GPIO->IEN |= (1<<RADIO_IRQ_LINE);
}

int gpio_odd = 0;

int status_count[32];

volatile int tx_packet_count = 0;
volatile int rx_packet_count = 0;
volatile int rx_error_count = 0;
volatile int rx_timeout_count = 0;
volatile int radio_rxreset_count = 0;
volatile int radio_overflow_count = 0;

void radio_rxdone(uint32_t status);
void radio_rxtimeout(uint32_t status);
void radio_rxerror(uint32_t status);
void radio_txdone(uint32_t status);

void GPIO_ODD_IRQHandler(void)
{
	uint32_t status;
	int i;
    GPIO_IntClear(1<<RADIO_IRQ_LINE);
    gpio_odd++;
    status = radio_read32(RREG(SYS_STATUS));
    if (status & STATUS_RX_DONE)
        radio_rxdone(status);
    if (status & STATUS_RX_ERROR)
    	radio_rxerror(status);
    if (status & STATUS_RX_TIMEOUT)
    	radio_rxtimeout(status);
    if (status & STATUS_TX_DONE)
    	radio_txdone(status);
    for (i = 0; i < 32; i++) {
    	if (status & (1<<i))
    		status_count[i]++;
    }
}

void radio_enable_interrupts(void);

void radio_init(bool loadlde)
{
    uint16_t val;
    uint32_t ldo_tune;

	radio_spi_init();

	/* If the radio was asleep then it needs to be woken up before it can be accessed */
	radio_wakeup_action();

	delay(1);

	/* Reset the radio */
	GPIO_PinModeSet(gpioPortC, 10, gpioModePushPull, 0);
	delay(1);
	GPIO_PinModeSet(gpioPortC, 10, gpioModeInput, 0);

	if (radio_deviceid() != 0xDECA0130)
		for (;;) ;

	/* Don't enable interrupts until we've reset the radio
	 * and we're sure we are talking to the right device.
	 */
	GPIO_PinModeSet(gpioPortC, 9, gpioModeInput, 0);
	GPIO_IntConfig(gpioPortC, 9, true, false, true);
	NVIC_ClearPendingIRQ(GPIO_ODD_IRQn);
	NVIC_EnableIRQ(GPIO_ODD_IRQn);

	radio_aon_wcfg = 0;

	radio_softreset();
	/* Reading OTP reliably requires this clock configuration */
	radio_setclocks(RADIO_FORCE_SYS_XTI);

    radio_write8(RREGO(EC_CTRL, 0), FIELDS(EC_CTRL, PLLLDT, 1));

    val = radio_otp_read32(OTP_XTAL_TRIM) & 0xffff;
    radio_otp_rev = (val >> 8) & 0xff;

    radio_trim_init = val & 0x1F;
    if (!radio_trim_init)
        radio_trim_init = 0x10; // Mid-range

    ldo_tune = radio_otp_read32(OTP_LDOTUNE_CAL_LOW);
    // Let's assume that the low 4 bytes will be non-zero if this is programmed
    if (ldo_tune != 0)
    {
        radio_write8(RREG(OTP_SF), FIELDS(OTP_SF, LDO_KICK, 1));
        radio_aon_wcfg |= FIELDS(AON_WCFG, ONW_LLDO, 1);
    }

    radio_chipid = radio_otp_read32(OTP_CHIP_ID);
    radio_lotid  = radio_otp_read32(OTP_LOT_ID);

    radio_xtal_trim(radio_trim_init);

    if (loadlde)
    {
    	radio_loadlde();
    	radio_aon_wcfg |= FIELDS(AON_WCFG, ONW_LLDE, 1);
    }
    else
    {
        uint32_t reg = radio_read32(RREG(PMSC_CTRL1));
        FIELDS_EDIT(reg, PMSC_CTRL1, LDERUNE, 0);
        radio_write32(RREG(PMSC_CTRL1), reg);
    }

    radio_setclocks(RADIO_ENABLE_ALL_SEQ);

    radio_write8(RREGO(AON_CFG1, 0), 0x00);

    radio_syscfg = radio_read32(RREG(SYS_CFG));

    radio_doublebuffer_enabled = !(radio_syscfg & FIELDS(SYS_CFG, DIS_DRXB, 1));

    /* We want interrupts for these events */
    radio_enable_interrupts();
}

void radio_enable_interrupts(void)
{
    radio_write32(RREG(SYS_MASK), STATUS_RX_ENABLE | STATUS_TX_ENABLE);
}

void radio_xtal_trim(uint8_t value)
{
    radio_write8(RREG(FS_XTALT), FIELDS(FS_XTALT, RESERVED, 3, XTALT, value));
}

void radio_setcallbacks(radio_callbacks *callbacks)
{
	radio_callback_txdone = callbacks->txdone;
	radio_callback_rxdone = callbacks->rxdone;
	radio_callback_rxerror = callbacks->rxerror;
	radio_callback_rxtimeout = callbacks->rxtimeout;
}

uint32_t radio_deviceid(void)
{
	return radio_read32(RREG(DEV_ID));
}

void radio_loadlde(void)
{
    radio_setclocks(RADIO_FORCE_LDE);
	radio_write16(RREG(OTP_CTRL), FIELDS(OTP_CTRL, LDELOAD, 1));
	delay(1);
    radio_setclocks(RADIO_ENABLE_ALL_SEQ);
}


/* fast_prf; true = 64MHz, false = 16MHz */

void radio_configlde(bool fast_prf)
{
	radio_write8(RREG(LDE_CFG1), 0x6c);
	radio_write16(RREG(LDE_CFG2), fast_prf ? 0x0607 : 0x1607);
}

static inline void radio_spiheader(uint8_t file, uint16_t reg, bool write)
{
    uint8_t b1 = file | (write?0x80:0);
    uint8_t b2 = reg & 0x7f;
    uint8_t b3 = reg >> 7;
//    uint8_t b[3] = {file | (write?0x80:0), reg & 0x7f, reg >> 7};
    if (reg)
        b1 |= 0x40;
    if (b3)
        b2 |= 0x80;

#if 1
    radio_spi_write(b1);
    if (write)
        radio_debug_write(b1);
    if (b2) {
        radio_spi_write(b2);
        if (write)
            radio_debug_write(b2);
    }
    if (b3) {
        radio_spi_write(b3);
        if (write)
            radio_debug_write(b3);
    }
#else
    radio_spi_write_burst(b, (reg)?((reg >> 7)?3:2):1);
#endif
}

void radio_read(uint8_t file, uint16_t reg, uint8_t *data, uint8_t len)
{
//	int i;
	bool e = radio_intoff();

    radio_spi_start();
    radio_spiheader(file, reg, false);

#if 1
    for (int i = 0; i < len; i++)
        data[i] = radio_spi_read();
#else
    radio_spi_read_burst(data, len);
#endif
    radio_spi_stop();

    radio_inton(e);
}

void radio_write(uint8_t file, uint16_t reg, uint8_t *data, uint8_t len)
{
//	int i;
	bool e = radio_intoff();

    radio_spi_start();
    radio_spiheader(file, reg, true);

#if 0
	radio_debug_write(len);
    for (int i = 0; i < len; i++) {
        radio_spi_write(data[i]);
        radio_debug_write(data[i]);
    }
#else
    radio_spi_write_burst(data, len);
#endif

    radio_spi_stop();

    radio_inton(e);
}

inline uint8_t radio_read8(uint8_t file, uint16_t reg)
{
	uint8_t data;
	radio_read(file, reg, &data, 1);
	return data;
}

inline void radio_write8(uint8_t file, uint16_t reg, uint8_t data)
{
	radio_write(file, reg, &data, 1);
}

inline uint16_t radio_read16(uint8_t file, uint16_t reg)
{
	uint16_t data;
	radio_read(file, reg, (uint8_t *)&data, 2);
	return data;
}

inline void radio_write16(uint8_t file, uint16_t reg, uint16_t data)
{
	radio_write(file, reg, (uint8_t *)&data, 2);
}

inline uint32_t radio_read32(uint8_t file, uint16_t reg)
{
	uint32_t data;
	radio_read(file, reg, (uint8_t *)&data, 4);
	return data;
}

inline void radio_write32(uint8_t file, uint16_t reg, uint32_t data)
{
	radio_write(file, reg, (uint8_t *)&data, 4);
}

void radio_syncbuffers(void)
{
    uint8_t status = radio_read32(RREGO(SYS_STATUS, 3));

    bool hsrbp = ((status & FIELDSO(SYS_STATUS, 3, HSRBP, 1)) != 0);
    bool icrbp = ((status & FIELDSO(SYS_STATUS, 3, HSRBP, 1)) != 0);

    if (hsrbp != icrbp)
    	radio_write8(RREGO(SYS_CTRL, 3), FIELDSO(SYS_CTRL, 3, HRBPT, 1));

}

void radio_doublebuffer(bool enable)
{
	FIELDS_EDIT(radio_syscfg, SYS_CFG, DIS_DRXB, !enable);
	radio_doublebuffer_enabled = enable;
	radio_write32(RREG(SYS_CFG), radio_syscfg);
}

void radio_autoreceive(bool enable)
{
	FIELDS_EDIT(radio_syscfg, SYS_CFG, RXAUTR, enable);
	radio_write32(RREG(SYS_CFG), radio_syscfg);
}

void radio_configure(radio_config_t *config)
{
    bool bw_wide = ((config->chan == 4) || (config->chan == 7)) ? true : false;
    uint16_t repc = repc_values[config->rx_pcode];
    uint8_t ch_index;

    if ((config->chan < 1) || (config->chan == 6) || (config->chan > 7))
    	return;

    ch_index = config->chan-1;
    if (config->chan == 7)
        	ch_index--;

    if(config->data_rate == RADIO_RATE_110K)
    {
        FIELDS_EDIT(radio_syscfg, SYS_CFG, RXM110K, 1);
        repc >>= 3;
    }
    else
    {
        FIELDS_EDIT(radio_syscfg, SYS_CFG, RXM110K, 0);
    }

    radio_long_frames = config->long_frames;
    radio_fs_plltune = fs_plltune_values[ch_index];
    radio_prf_high = config->prf_high;

    FIELDS_EDIT(radio_syscfg, SYS_CFG, PHR_MODE, radio_long_frames?3:0);

    radio_write32(RREG(SYS_CFG), radio_syscfg);
    radio_write16(RREG(LDE_REPC), repc);
	radio_configlde(radio_prf_high);

    radio_write32(RREG(FS_PLLCFG), fs_pllcfg_values[ch_index]);
    radio_write8(RREG(FS_PLLTUNE), radio_fs_plltune);
    radio_write8(RREG(RF_RXCTRLH), bw_wide?0xBC:0xD8);
    radio_write32(RREG(RF_TXCTRL), rf_txctrl_values[ch_index]);
    radio_write16(RREG(DRX_TUNE0B), drx_tune0b_values[config->data_rate * 2 + (config->ns_sfd?1:0)]);
    radio_write16(RREG(DRX_TUNE1A), config->prf_high?0x008D:0x0087);
    radio_write16(RREG(DRX_TUNE1B), (config->tx_plen > RADIO_PLEN_1024) ? 0x0064 : ((config->tx_plen == RADIO_PLEN_64)?0x0010:0x0020));
    radio_write8(RREG(DRX_TUNE4H), (config->tx_plen == RADIO_PLEN_64)?0x0010:0x0028);
    radio_write32(RREG(DRX_TUNE2), drx_tune2_values[config->rx_pac * 2 + (config->prf_high?1:0)]);
    radio_write16(RREG(DRX_SFDTOC), (config->sfd_timeout>0)?config->sfd_timeout:RADIO_SFD_TIMEOUT_DEFAULT);
    radio_write32(RREG(AGC_TUNE2), 0x2502A907);
    radio_write16(RREG(AGC_TUNE1), config->prf_high?0x889B:0x8870);

    if(config->ns_sfd)
        radio_write8(RREG(USR_SFD), sfd_length_values[config->data_rate]);

    radio_write32(RREG(CHAN_CTRL), FIELDS(CHAN_CTRL,
    		                   TX_CHAN, config->chan,
    		                   RX_CHAN, config->chan,
							   RXPRF, config->prf_high?2:1,
							   TNSSFD, config->ns_sfd,
							   RNSSFD, config->ns_sfd,
							   DWSFD, config->ns_sfd,
							   TX_PCODE, config->tx_pcode,
							   RX_PCODE, config->rx_pcode));

    radio_tx_fctrl = FIELDS(TX_FCTRL, TXPRF, config->prf_high?2:1,
    		                          TXPSR, config->tx_plen >> 2,
									  PE, config->tx_plen & 3,
									  TXBR, config->data_rate);
    radio_write32(RREG(TX_FCTRL), radio_tx_fctrl);

    /* Force reinitialisation of SFD sequence */
    radio_write8(RREG(SYS_CTRL), FIELDS(SYS_CTRL, TXSTRT, 1, TRXOFF, 1));
}

void radio_settxpower(uint32_t power)
{
	radio_write32(RREG(TX_POWER), power);
}

void radio_smarttxpowercontrol(bool enabled)
{
    uint8_t reg;

    reg = radio_read8(RREGO(SYS_CFG, 2));

    FIELDS_EDITO(reg, SYS_CFG, 2, DIS_STXP, enabled?0:1);

    radio_write8(RREGO(SYS_CFG, 2), reg);
}

/*
 * time is in units of 1.0256 us (512/499.2MHz)
 * 0 = disabled
 */
void radio_setrxtimeout(uint16_t time)
{
    uint8_t reg;

    reg = radio_read8(RREGO(SYS_CFG, 3));

    FIELDS_EDITO(reg, SYS_CFG, 3, RXWTOE, (time>0)?1:0);

    if(time > 0)
    	radio_write16(RREG(RX_FWTO), time);

    radio_write8(RREGO(SYS_CFG, 3), reg);
}

/* The actual payload will be 2 bytes longer than specified here. Don't
 * write the CRC with this function.
 */
bool radio_writepayload(uint8_t *data, uint16_t len, uint16_t offset)
{
	if ((offset + len + 2) > 1024)
		return false;

	radio_write(RREGO(TX_BUFFER, offset), data, len);

	return true;
}

/* Include the length of the CRC when calling this function */
void radio_txprepare(uint16_t len, uint16_t offset, bool ranging)
{
    radio_write32(RREG(TX_FCTRL), radio_tx_fctrl | FIELDS(TX_FCTRL,
    		    TFLEN, len,
				TXBOFFS, offset,
				TR, ranging?1:0
    		));
}

void radio_gettime(uint8_t *time)
{
	radio_read(RREG(SYS_TIME), time, 5);

}
void radio_setstarttime(uint32_t time)
{
	/* The bottom 9 bits of this register are ignored */
    radio_write32(RREGO(DX_TIME, 1), time);
}

void radio_readtxtimestamp(uint8_t *time)
{
	radio_read(RREG(TX_TIME), time, 5);
}

void radio_readrxtimestamp(uint8_t *time)
{
	radio_read(RREG(RX_TIME), time, 5);
}

bool radio_rxstart(bool delayed)
{
	uint32_t value = FIELDS(SYS_CTRL, RXENAB, 1, RXDLYE, delayed?1:0);
	radio_syncbuffers();
	radio_write32(RREG(SYS_CTRL), value);
	if (delayed) {
	    if (radio_read8(RREGO(SYS_STATUS, 3)) & FIELDSO(SYS_STATUS, 3, HPDWARN, 1)) {
	    	radio_txrxoff();
	    	return false;
	    }
	}
	return true;
}

bool radio_txstart(bool delayed)
{
	uint32_t value = FIELDS(SYS_CTRL, TXSTRT, 1, TXDLYS, delayed?1:0);
	radio_write32(RREG(SYS_CTRL), value);
	if (delayed) {
		uint16_t status = radio_read16(RREGO(SYS_STATUS, 3));
	    if (status & FIELDSO(SYS_STATUS, 3, HPDWARN, 1, TXPUTE, 1)) {
	    	radio_txrxoff();
	    	return false;
	    }
	}
	return true;
}

void radio_txrxoff(void)
{
	bool e = radio_intoff();
	radio_write32(RREG(SYS_MASK), 0);
	radio_write32(RREG(SYS_CTRL), FIELDS(SYS_CTRL, TRXOFF, 1));
	radio_write32(RREG(SYS_STATUS), STATUS_ALL_CLEAR);
	radio_syncbuffers();
    radio_enable_interrupts();
	radio_inton(e);
}

void radio_txdone(uint32_t status)
{
	radio_write32(RREG(SYS_STATUS), STATUS_TX_CLEAR);

	tx_packet_count++;

	if (radio_callback_txdone)
		radio_callback_txdone();
}

void radio_rxdone(uint32_t status)
{
	radio_write32(RREG(SYS_STATUS), STATUS_RX_DONE_CLEAR);

	rx_packet_count++;

	if (radio_callback_rxdone)
		radio_callback_rxdone();
}

void radio_rxtimeout(uint32_t status)
{
	radio_write32(RREG(SYS_STATUS), STATUS_RX_TIMEOUT_CLEAR);

	rx_timeout_count++;

	if (radio_callback_rxtimeout)
		radio_callback_rxtimeout();
}

void radio_rxerror(uint32_t status)
{
    radio_write32(RREG(SYS_STATUS), STATUS_RX_ERROR_CLEAR);

    if (status & STATUS_RX_ERROR_RESET) {
        radio_rxreset();
        radio_rxreset_count++;
        delay(1); // XXX
    }

    // Clear SYS_CTRL_RXENAB
	radio_write32(RREG(SYS_CTRL), 0);

	rx_error_count++;

	if (radio_callback_rxerror)
		radio_callback_rxerror();
}

bool radio_overflow(void)
{
    uint8_t status = radio_read32(RREGO(SYS_STATUS, 2));

    if (!(status & FIELDSO(SYS_STATUS, 2, RXOVRR, 1)))
    	return false;

    radio_txrxoff();
    radio_rxreset();
    radio_overflow_count++;
//    delay(1); // XXX Do we need this?

    return true;
}

int radio_getpayload(void *data, int maxlen)
{
	int len = radio_read16(RREG(RX_FINFO)) & 0x3ff;

    if (len > maxlen)
	    len = maxlen;

    radio_read(RREG(RX_BUFFER), data, len);

    if (radio_doublebuffer_enabled)
    	radio_write8(RREGO(SYS_CTRL, 3), FIELDSO(SYS_CTRL, 3, HRBPT, 1));

	return len;
}

void radio_rxreset(void)
{
    radio_write8(RREGO(PMSC_CTRL0, 3), FIELDSO(PMSC_CTRL0, 3, SOFTRESET, 0xE));
    radio_write8(RREGO(PMSC_CTRL0, 3), FIELDSO(PMSC_CTRL0, 3, SOFTRESET, 0xF));
}


void radio_disablesequencing(void)
{
    radio_setclocks(RADIO_FORCE_SYS_XTI);
    radio_write16(RREG(PMSC_CTRL1), 0x0000);
}

void radio_softreset(void)
{
    radio_disablesequencing();

    radio_write16(RREGO(AON_WCFG, 0), 0x00);
    radio_write8(RREGO(AON_CFG0, 0), 0x00);

    radio_aonarrayupload();

    radio_write8(RREGO(PMSC_CTRL0, 3), FIELDSO(PMSC_CTRL0, 3, SOFTRESET, 0));
    delay(1);
    radio_write8(RREGO(PMSC_CTRL0, 3), FIELDSO(PMSC_CTRL0, 3, SOFTRESET, 0xF));
}

void radio_aonconfigupload(void)
{
    radio_write8(RREG(AON_CTRL), FIELDS(AON_CTRL, UPL_CFG, 1));
    radio_write8(RREG(AON_CTRL), 0x00);
}

void radio_aonarrayupload(void)
{
    radio_write8(RREG(AON_CTRL), 0x00);
    radio_write8(RREG(AON_CTRL), FIELDS(AON_CTRL, SAVE, 1));
}

void radio_antenna_delay_rx(uint16_t delay)
{
	radio_write16(RREG(LDE_RXANTD), delay);
}

void radio_antenna_delay_tx(uint16_t delay)
{
	radio_saved_antenna_delay_tx = delay;
	radio_write16(RREG(TX_ANTD), delay);
}


void radio_setclocks(int clocks)
{
    uint16_t reg;

    reg = radio_read16(RREG(PMSC_CTRL0));
    switch(clocks)
    {
        case RADIO_ENABLE_ALL_SEQ:
        {
        	FIELDS_EDIT(reg, PMSC_CTRL0, SYSCLKS, 0, RXCLKS, 0, TXCLKS, 0, FACE, 0, LDE, 0);
        }
        break;
        case RADIO_FORCE_SYS_XTI:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, SYSCLKS, 1);
        }
        break;
        case RADIO_FORCE_SYS_PLL:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, SYSCLKS, 2);
        }
        break;
        case RADIO_READ_ACC_ON:
        {
        	FIELDS_EDIT(reg, PMSC_CTRL0, AMCE, 1, FACE, 1, RXCLKS, 2);
        }
        break;
        case RADIO_READ_ACC_OFF:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, AMCE, 0, FACE, 0, RXCLKS, 0);
        }
        break;
        case RADIO_FORCE_OTP_ON:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, OTP, 1);
        }
        break;
        case RADIO_FORCE_OTP_OFF:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, OTP, 0);
        }
        break;
        case RADIO_FORCE_TX_PLL:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, TXCLKS, 2);
        }
        break;
        case RADIO_FORCE_RX_PLL:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, RXCLKS, 2);
        }
        break;
        case RADIO_FORCE_TXRX_PLL:
        {
            FIELDS_EDIT(reg, PMSC_CTRL0, TXCLKS, 2, RXCLKS, 2);
        }
        break;
        case RADIO_FORCE_LDE:
        {
            reg = FIELDS(PMSC_CTRL0, OTP, 1, LDE, 1, SYSCLKS, 1);
        }
        break;
        default:
        break;
    }


    // Need to write lower byte separately before setting the higher byte(s)
    radio_write8(RREGO(PMSC_CTRL0, 0), reg & 0xff);
    radio_write8(RREGO(PMSC_CTRL0, 1), reg >> 8);
}

void radio_otp_read(uint32_t address, uint32_t *array, uint8_t length)
{
    radio_setclocks(RADIO_FORCE_SYS_XTI);

    for (int i=0; i < length; i++) {
        radio_write16(RREG(OTP_ADDR), address+i);
        radio_write8(RREG(OTP_CTRL), FIELDS(OTP_CTRL, OTPREAD, 1, OTPRDEN, 1));
        radio_write8(RREG(OTP_CTRL), 0x00);
        array[i] = radio_read32(RREG(OTP_RDAT));
    }

    radio_setclocks(RADIO_ENABLE_ALL_SEQ);
}

uint32_t radio_otp_read32(uint32_t address)
{
    radio_write16(RREG(OTP_ADDR), address);
    radio_write8(RREG(OTP_CTRL), FIELDS(OTP_CTRL, OTPREAD, 1, OTPRDEN, 1));
    radio_write8(RREG(OTP_CTRL), 0x00);
    return radio_read32(RREG(OTP_RDAT));
}

uint32_t radio_otp_read16(uint32_t address)
{
    radio_write16(RREG(OTP_ADDR), address);
    radio_write8(RREG(OTP_CTRL), FIELDS(OTP_CTRL, OTPREAD, 1, OTPRDEN, 1));
    radio_write8(RREG(OTP_CTRL), 0x00);
    return radio_read16(RREG(OTP_RDAT));
}

void radio_configsleep(uint16_t mode, uint8_t wake)
{
    mode |= radio_aon_wcfg;
    radio_write16(RREG(AON_WCFG), mode);
    radio_write8(RREG(AON_CFG0), wake);
}

void radio_entersleep(void)
{
    radio_aonarrayupload();
}

void radio_wakeup_restore(void)
{
    radio_leds_restore();
	radio_configlde(radio_prf_high);
    radio_write8(RREG(FS_PLLTUNE), radio_fs_plltune);
    /* Let's hope that AGC_TUNE2 is actually set - AGC_TUNE1 is mentioned
     * twice in the datasheet so we presume this is an error
     */
    radio_antenna_delay_tx(radio_saved_antenna_delay_tx);
}

/* Note that a wakeup can cause a transfer of AON memory to core registers.
 * Access to those core registers should be avoided until the transfer is
 * complete. The datasheet doesn't indicate how long this takes or how to
 * tell once it's done. The Tx buffer is not part of this set.
 */
void radio_wakeup_action(void)
{
    radio_spi_wakeup_assert();
    /* Needs to be at least 500us */
    delay(1);
    radio_spi_wakeup_deassert();
    delay(5);
}

void radio_wakeup(void)
{
	radio_wakeup_action();
    radio_wakeup_restore();
}

void radio_cswakeup_action(void)
{
    radio_spi_start();
    delay(1);
    radio_spi_stop();
    delay(5);
}

void radio_cswakeup(void)
{
	radio_cswakeup_action();
    radio_wakeup_restore();
}

void radio_leds_restore(void)
{
	bool on = radio_ledstate;
	int time = radio_ledtime;

    uint32_t reg = radio_read32(RREG(PMSC_CTRL0));
    FIELDS_EDIT(reg, PMSC_CTRL0, KHZCLKEN, on, GPDRN, 1, GPDCE, 1, GPRN, 1, GPCE, 1);
    radio_write32(RREG(PMSC_CTRL0), reg);

    radio_write32(RREG(GPIO_MODE), FIELDS(GPIO_MODE, MSGP0, on, MSGP1, on, MSGP2, on, MSGP3, on));
    radio_write32(RREG(PMSC_LEDC), FIELDS(PMSC_LEDC, BLNKEN, on, BLINK_TIM, time));
}

/* Some of these bits aren't preserved over sleep, so it's best to call this again after wakeup */
void radio_leds(bool on, int time)
{
	radio_ledstate = on;
	radio_ledtime = time;
	radio_leds_restore();
}

void radio_gpio(int pin, int mode, int dir, int value)
{
    if ((pin < 0) || (pin > 8))
        return;
    int modepin = (pin + 3) * 2;

    uint32_t reg = radio_read32(RREG(GPIO_MODE));
    reg = reg & ~(3 << modepin);
    reg = reg | (mode << modepin);
    radio_write32(RREG(GPIO_MODE), reg);

    int dirpin = pin;
    if (pin > 3)
        dirpin += 4;
    if (pin > 7)
        dirpin += 4;
    radio_write32(RREG(GPIO_DIR), (dir << dirpin) | (1 << (dirpin + 4)));
    radio_write32(RREG(GPIO_DOUT), (value << dirpin) | (1 << (dirpin + 4)));
}

void radio_wakeup_adc_readings(uint8_t *voltage, uint8_t *temperature)
{
	uint16_t reading = radio_read16(RREG(TC_SARW));
	if (voltage)
		*voltage = reading & 0xff;
	if (temperature)
		*temperature = reading >> 8;
}

void radio_read_adc_cal(uint8_t *voltage, uint8_t *temperature)
{
	if (voltage)
		*voltage = radio_otp_read16(OTP_VOLTAGE_CAL) & 0xff;
	if (temperature)
		*temperature = radio_otp_read16(OTP_TEMPERATURE_CAL) & 0xff;
}

uint32_t radio_state(void)
{
    return radio_read32(RREG(SYS_STATE));
}

#endif
