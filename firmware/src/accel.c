/* accel.c */

#include <stdbool.h>
#include "em_gpio.h"

#include "accel.h"
#include "accel_spi.h"
#include "accel_reg.h"
#include "time.h"


#define PORT_INT gpioPortC
#define PIN_INT  4
#define NVIC_INT  GPIO_EVEN_IRQn
#define GPIO_INT 4
#define accel_interrupt_handler GPIO_EVEN_IRQHandler

static bool accel_try_init(int version);
static void accel_init_sequence(void);

void accel_delay_ms(int ms)
{
	int target = ms * 3500; // XXX calibrate this
    for (volatile int count = 0; count < target; count++) ;
}

static inline bool accel_intoff(void)
{
	bool enabled = GPIO->IEN & (1<<GPIO_INT);
	if (enabled)
		GPIO->IEN &= ~(1<<GPIO_INT);
	return enabled;
}

static inline void accel_inton(bool enable)
{
	if (enable)
        GPIO->IEN |= (1<<GPIO_INT);
}

bool accel_init(void)
{
    accel_spi_init();

    if (!(accel_try_init(2) || accel_try_init(1)))
    	return false;

    accel_config_interrupts();

    GPIO_PinModeSet(PORT_INT, PIN_INT, gpioModeInput, 0);
	GPIO_IntConfig(PORT_INT, PIN_INT, true, false, true);
	NVIC_ClearPendingIRQ(NVIC_INT);
	NVIC_EnableIRQ(NVIC_INT);

	return true;
}

static bool accel_try_init(int version) {
    accel_spi_version(version);
    accel_init_sequence();
    return (accel_read(0x0f) == 0x43);
}

static void accel_init_sequence(void) {
    accel_write(MODE_C, STANDBY);
    accel_delay_ms(10);

    accel_write(RESET_C, RESET);
    accel_delay_ms(1);

    /* This is not in the datasheet, but trying to write FREG_1 in SLEEP mode seems to fail. */
    accel_write(MODE_C, STANDBY);
    accel_delay_ms(10);

    accel_write(FREG_1, SPI_EN);
    accel_write(INIT_1, INIT_VALUE);
    accel_write(DMX, DMX_INIT);
    accel_write(DMY, DMY_INIT);
    accel_write(INIT_2, 0);
    accel_write(INIT_3, 0);
}

uint8_t accel_read(uint8_t addr)
{
    uint8_t data;

    addr = addr | 0xc0;

    accel_spi_start();
    accel_spi_write(addr);

    data = accel_spi_read();
    accel_spi_stop();

    return data;
}

void accel_read_multiple(uint8_t *data, uint8_t addr, int len)
{
    addr = addr | 0xc0;

    accel_spi_start();
    accel_spi_write(addr);

    while (len--)
        *(data++) = accel_spi_read();
    accel_spi_stop();
}


void accel_write(uint8_t addr, uint8_t data)
{
    accel_spi_start();

    addr = addr | 0x40;

    accel_spi_write(addr);
    accel_spi_write(data);

    accel_spi_stop();
}

void accel_config_interrupts(void)
{
	bool irq = accel_intoff();
	accel_write(INTR_C, IPP | IAH | INT_WAKE);
	accel_inton(irq);
}

void accel_config_power_mode(int wake_mode, int sniff_mode)
{
	bool irq = accel_intoff();
	accel_write(PMCR, SPM(sniff_mode) | CSPM(wake_mode));
	accel_inton(irq);
}

void accel_config_rate(int rate)
{
	bool irq = accel_intoff();
	accel_write(RATE_1, rate);
	accel_inton(irq);
}

void accel_config_range_resolution(int range, int res)
{
	bool irq = accel_intoff();
	accel_write(RANGE_C, RANGE(range) | RES(res));
	accel_inton(irq);
}

void accel_config_sniff_rate(int sniff_rate, int standby_rate)
{
	bool irq = accel_intoff();
	accel_write(SNIFF_C, SNIFF_SR(sniff_rate) | STB_RATE(standby_rate));
	accel_inton(irq);
}

void accel_config_threshold(int x, int y, int z, int shift)
{
	bool irq = accel_intoff();
	uint8_t cf = accel_read(SNIFFCF_C) & SNIFF_CNTEN;
	cf |= SNIFF_MUX(shift);
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_TH_X) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(x));
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_TH_Y) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(y));
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_TH_Z) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(z));
	accel_inton(irq);
}

void accel_config_detection_count(int x, int y, int z, int enable)
{
	bool irq = accel_intoff();
    uint8_t cf = accel_read(SNIFFCF_C) & SNIFF_MUX(7);
    if (enable)
        cf |= SNIFF_CNTEN;
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_X_COUNT) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(x));
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_Y_COUNT) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(y));
	accel_write(SNIFFCF_C, SNIFF_THADR(SNIFF_Z_COUNT) | cf);
	accel_write(SNIFFTH_C, SNIFF_TH(z));
	accel_inton(irq);
}

/* Call this after configuring the threshold and detection count */
void accel_config_sniff_mode(bool and, bool c2b)
{
	uint8_t th = accel_read(SNIFFTH_C) & SNIFF_TH(0x3f);
	if (and)
		th |= SNIFF_AND_OR;
	if (c2b)
		th |= SNIFF_MODE;
	accel_write(SNIFFTH_C, th);
}

void accel_enter_mode(int mode)
{
	bool irq = accel_intoff();
	uint8_t reg = accel_read(MODE_C);
	reg &= ~MCTRL(7);
	reg |= MCTRL(mode);
	accel_write(MODE_C, reg);
    accel_delay_ms(3);
    accel_inton(irq);
}

void accel_enable_axis(bool x, bool y, bool z)
{
	bool irq = accel_intoff();
	uint8_t reg = accel_read(MODE_C);
	reg &= ~X_AXIS_PD;
	reg &= ~Y_AXIS_PD;
	reg &= ~Z_AXIS_PD;
	if (!x)
		reg |= X_AXIS_PD;
	if (!y)
		reg |= Y_AXIS_PD;
	if (!z)
		reg |= Z_AXIS_PD;
	accel_write(MODE_C, reg);
	accel_inton(irq);
}

void accel_readings(uint16_t *x, uint16_t *y, uint16_t *z)
{
	bool irq = accel_intoff();
	uint8_t data[6];
	accel_read_multiple(data, XOUT_LSB, 6);
	*x = data[0] | (data[1] << 8);
	*y = data[2] | (data[3] << 8);
	*z = data[4] | (data[5] << 8);
	accel_inton(irq);
}

void accel_test(int x, int y, int z)
{
	bool irq = accel_intoff();

    uint8_t reg;

    reg = DMX_INIT;
    if (x > 0)
    	reg |= DPX;
    if (x < 0)
    	reg |= DNX;
    accel_write(DMX, reg);

    reg = DMY_INIT;
    if (y > 0)
    	reg |= DPY;
    if (y < 0)
    	reg |= DNY;
    accel_write(DMY, reg);

    reg = DMZ_INIT;
    if (z > 0)
    	reg |= DPZ;
    if (z < 0)
    	reg |= DNZ;
    accel_write(DMZ, reg);

    accel_inton(irq);
}

static volatile bool accel_interrupt_fired_state = false;
static volatile uint32_t accel_interrupt_last_fired_at = 0;

void accel_interrupt_handler(void)
{
    GPIO_IntClear(1<<GPIO_INT);
	uint8_t status = accel_read(STATUS_2);
	accel_write(STATUS_2, status); /* Clear interrupts */

	/* XXX for now, just re-enable sniff mode */
	accel_enter_mode(STANDBY);
	accel_enter_mode(SNIFF);

	accel_interrupt_fired_state = true;
	accel_interrupt_last_fired_at = time_now();
}

bool accel_interrupt_fired(void)
{
	bool state = accel_interrupt_fired_state;

	if (state)
		accel_interrupt_fired_state = false;

	return state;
}

uint32_t accel_last_activity(void)
{
	return accel_interrupt_last_fired_at;
}

bool accel_activity_detected(void)
{
	return false;
}
