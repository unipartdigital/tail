/*
 * IEEE 802.15.4 TTY-based Tail board driver
 *
 * Copyright (C) 2017 Michael Brown <mbrown@fensystems.co.uk>
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

#ifndef _TTYTAIL_H
#define _TTYTAIL_H

#include <linux/tty.h>
#include <linux/tty_ldisc.h>
#include <linux/workqueue.h>
#include <net/mac802154.h>

/** Line discipline identifier
 *
 * This is, obviously, not an officially allocated number.
 */
#define X_N_TAIL (NR_LDISCS - 1)

/** An IEEE 802.15.4 TTY-based Tail board device */
struct ttytail {
	/** TTY device */
	struct tty_struct *tty;
	/** IEEE 802.15.4 device */
	struct ieee802154_hw *hw;
	/** Generic device (for debug messages) */
	struct device *dev;
	/** Transmit work queue */
	struct work_struct tx_work;
};

#endif /* _TTYTAIL_H */
