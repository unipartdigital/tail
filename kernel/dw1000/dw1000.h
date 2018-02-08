/*
 * DecaWave DW1000 IEEE 802.15.4 UWB wireless driver
 *
 * Copyright (C) 2018 Michael Brown <mbrown@fensystems.co.uk>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301, USA.
 *
 */

#ifndef __DW1000_H
#define __DW1000_H

#include <linux/device.h>
#include <linux/regmap.h>

/* SPI bus header */
struct dw1000_spi_header {
	/* Register file and command */
	uint8_t command;
	/* Low order 7 bits and extended address indicator */
	uint8_t low;
	/* High order 8 bits */
	uint8_t high;
} __packed;

/* SPI bus header command flags */
#define DW1000_WRITE 0x80
#define DW1000_OFFSET 0x40

/* SPI bus header extended offset present flags */
#define DW1000_EXTENDED 0x80

/* SPI bus header extended offset shift */
#define DW1000_EXTENDED_SHIFT 7

/* Register files */
#define DW1000_DEV_ID		0x00
#define DW1000_DEV_ID_LEN	4
#define DW1000_EUI		0x01
#define DW1000_EUI_LEN		8
#define DW1000_PANADR		0x03
#define DW1000_PANADR_LEN	4
#define DW1000_SYS_CFG		0x04
#define DW1000_SYS_CFG_LEN	4
#define DW1000_SYS_TIME		0x06
#define DW1000_SYS_TIME_LEN	5
#define DW1000_TX_FCTRL		0x08
#define DW1000_TX_FCTRL_LEN	5
#define DW1000_TX_BUFFER	0x09
#define DW1000_TX_BUFFER_LEN	1024
#define DW1000_DX_TIME		0x0a
#define DW1000_DX_TIME_LEN	5
#define DW1000_RX_FWTO		0x0c
#define DW1000_RX_FWTO_LEN	2
#define DW1000_SYS_CTRL		0x0d
#define DW1000_SYS_CTRL_LEN	4
#define DW1000_SYS_MASK		0x0e
#define DW1000_SYS_MASK_LEN	4
#define DW1000_SYS_STATUS	0x0f
#define DW1000_SYS_STATUS_LEN	5
#define DW1000_RX_FINFO		0x10
#define DW1000_RX_FINFO_LEN	4
#define DW1000_RX_BUFFER	0x11
#define DW1000_RX_BUFFER_LEN	1024
#define DW1000_RX_FQUAL		0x12
#define DW1000_RX_FQUAL_LEN	8
#define DW1000_RX_TTCKI		0x13
#define DW1000_RX_TTCKI_LEN	4
#define DW1000_RX_TTCKO		0x14
#define DW1000_RX_TTCKO_LEN	5
#define DW1000_RX_TIME		0x15
#define DW1000_RX_TIME_LEN	14
#define DW1000_TX_TIME		0x17
#define DW1000_TX_TIME_LEN	10
#define DW1000_TX_ANTD		0x18
#define DW1000_TX_ANTD_LEN	2
#define DW1000_ACK_RESP_T	0x1a
#define DW1000_ACK_RESP_T_LEN	4
#define DW1000_RX_SNIFF		0x1d
#define DW1000_RX_SNIFF_LEN	4
#define DW1000_TX_POWER		0x1e
#define DW1000_TX_POWER_LEN	4
#define DW1000_CHAN_CTRL	0x1f
#define DW1000_CHAN_CTRL_LEN	4
#define DW1000_USR_SFD		0x21
#define DW1000_USR_SFD_LEN	41
#define DW1000_AGC_CTRL		0x23
#define DW1000_AGC_CTRL_LEN	33
#define DW1000_EXT_SYNC		0x24
#define DW1000_EXT_SYNC_LEN	12
#define DW1000_ACC_MEM		0x25
#define DW1000_ACC_MEM_LEN	4064 /* sic */
#define DW1000_GPIO_CTRL	0x26
#define DW1000_GPIO_CTRL_LEN	44
#define DW1000_DRX_CONF		0x27
#define DW1000_DRX_CONF_LEN	44
#define DW1000_RF_CONF		0x28
#define DW1000_RF_CONF_LEN	58
#define DW1000_TX_CAL		0x2a
#define DW1000_TX_CAL_LEN	52
#define DW1000_FS_CTRL		0x2b
#define DW1000_FS_CTRL_LEN	21
#define DW1000_AON		0x2c
#define DW1000_AON_LEN		12
#define DW1000_OTP_IF		0x2d
#define DW1000_OTP_IF_LEN	18
#define DW1000_LDE_CTRL		0x2e
#define DW1000_LDE_CTRL_LEN	0x2806
#define DW1000_DIG_DIAG		0x2f
#define DW1000_DIG_DIAG_LEN	41
#define DW1000_PMSC		0x36
#define DW1000_PMSC_LEN		48

/* Device ID register file layout */
struct dw1000_dev_id {
	/* Version and revision */
	uint8_t ver_rev;
	/* Model */
	uint8_t model;
	/* Register identification tag */
	uint16_t ridtag;
} __packed;

/* Expedit register identification tag */
#define DW1000_RIDTAG_MAGIC 0xdeca

/* Register map parameters */
#define DW1000_REG_BITS 16
#define DW1000_VAL_BITS 8

/* Register map descriptor */
struct dw1000_regmap_config {
	/* Offset within DW1000 device structure */
	size_t offset;
	/* Register file */
	unsigned int file;
	/* Register offset shift */
	unsigned int shift;
	/* Register map configuration */
	struct regmap_config config;
};

/* Register map */
struct dw1000_regmap {
	/* Register map */
	struct regmap *regs;
	/* Containing DW1000 device */
	struct dw1000 *dw;
	/* Register map configuration */
	const struct dw1000_regmap_config *config;
};

/* DW1000 device */
struct dw1000 {
	struct spi_device *spi;
	struct dw1000_regmap dev_id;
	struct dw1000_regmap eui;
	struct dw1000_regmap panadr;
	struct dw1000_regmap sys_cfg;
	struct dw1000_regmap sys_time;
	struct dw1000_regmap tx_fctrl;
	struct dw1000_regmap tx_buffer;
	struct dw1000_regmap dx_time;
	struct dw1000_regmap rx_fwto;
	struct dw1000_regmap sys_ctrl;
	struct dw1000_regmap sys_mask;
	struct dw1000_regmap sys_status;
	struct dw1000_regmap rx_finfo;
	struct dw1000_regmap rx_buffer;
	struct dw1000_regmap rx_fqual;
	struct dw1000_regmap rx_ttcki;
	struct dw1000_regmap rx_ttcko;
	struct dw1000_regmap rx_time;
	struct dw1000_regmap tx_time;
	struct dw1000_regmap tx_antd;
	struct dw1000_regmap ack_resp_t;
	struct dw1000_regmap rx_sniff;
	struct dw1000_regmap tx_power;
	struct dw1000_regmap chan_ctrl;
	struct dw1000_regmap usr_sfd;
	struct dw1000_regmap agc_ctrl;
	struct dw1000_regmap ext_sync;
	struct dw1000_regmap acc_mem;
	struct dw1000_regmap gpio_ctrl;
	struct dw1000_regmap drx_conf;
	struct dw1000_regmap rf_conf;
	struct dw1000_regmap tx_cal;
	struct dw1000_regmap fs_ctrl;
	struct dw1000_regmap aon;
	struct dw1000_regmap otp_if;
	struct dw1000_regmap lde_ctrl;
	struct dw1000_regmap dig_diag;
	struct dw1000_regmap pmsc;
};

#endif /* __DW1000_H */
