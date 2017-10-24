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

#include <linux/module.h>
#include "ttytail.h"

#define TTYTAIL_INIT "\r\n" "reset\r\n" "echo 0\r\n" "config eui\r\n" "rx\r\n"
#define TTYTAIL_RESET "\r\n" "reset\r\n"

/*****************************************************************************
 *
 * Transmit datapath
 *
 */

static void ttytail_tx_worker(struct work_struct *work)
{
	struct ttytail *ttytail = container_of(work, struct ttytail, tx.work);
	struct ttytail_line *line = &ttytail->tx.line;
	char *data;
	size_t remaining;
	size_t actual;

	remaining = (line->len - line->offset);
	if (remaining) {
		data = &line->data[line->offset];
		actual = ttytail->tty->ops->write(ttytail->tty, data,
						  remaining);
		line->offset += actual;
		if (actual == remaining)
			wake_up_interruptible(&ttytail->tx.wait);
	}
}

static void ttytail_tx_start(struct ttytail *ttytail, const char *fmt, ...)
{
	struct ttytail_line *line = &ttytail->tx.line;
	va_list args;

	WARN_ON(line->offset != line->len);

	va_start(args, fmt);
	if (fmt)
		vsnprintf(line->data, sizeof(line->data), fmt, args);
	va_end(args);
	dev_info(ttytail->dev, "> %s", line->data);

	line->offset = 0;
	line->len = strlen(line->data);

	schedule_work(&ttytail->tx.work);
}

static void ttytail_tx_cancel(struct ttytail *ttytail)
{
	cancel_work_sync(&ttytail->tx.work);
}

static void ttytail_tx_wait(struct ttytail *ttytail)
{
	struct ttytail_line *line = &ttytail->tx.line;

	wait_event_interruptible(ttytail->tx.wait, (line->offset == line->len));
}

/*****************************************************************************
 *
 * Receive datapath
 *
 */

static int ttytail_rx_byte(struct ttytail *ttytail)
{
	struct ttytail_line *line = &ttytail->rx.line;
	unsigned int byte;
	int len;
	int matched;

	matched = sscanf(&line->data[line->offset], "%x%n", &byte, &len);
	if (matched != 1) {
		dev_err(ttytail->dev, "invalid byte at \"%s\" (matched %d)\n",
			&line->data[line->offset], matched);
		return -EINVAL;
	}

	line->offset += len;
	return byte;
}

static int ttytail_rx_bytes(struct ttytail *ttytail, uint8_t *data, size_t len)
{
	struct ttytail_line *line = &ttytail->rx.line;
	int byte;

	while (1) {
		byte = ttytail_rx_byte(ttytail);
		if (byte < 0)
			return byte;
		*data++ = byte;
		if (--len == 0)
			return 0;
		if (line->data[line->offset] != ' ') {
			dev_err(ttytail->dev, "invalid separator at \"%s\"\n",
				&line->data[line->offset]);
			return -EINVAL;
		}
		line->offset++;
	}
}

static void ttytail_rx_reset(struct ttytail *ttytail)
{
	memset(&ttytail->rx.line, 0, sizeof(ttytail->rx.line));
}

static void ttytail_rx_packet(struct ttytail *ttytail, size_t len)
{
	int err;

	if (ttytail->rx.skb) {
		dev_err(ttytail->dev, "missing RX timestamp\n");
		dev_consume_skb_any(ttytail->rx.skb);
	}

	ttytail->rx.skb = alloc_skb(len, GFP_ATOMIC);
	if (!ttytail->rx.skb) {
		dev_err(ttytail->dev, "failed allocation of %zd bytes\n", len);
		goto drop;
	}

	err = ttytail_rx_bytes(ttytail, skb_put(ttytail->rx.skb, len), len);
	if (err) {
		dev_err(ttytail->dev, "invalid packet\n");
		goto drop;
	}

 drop:
	ttytail_rx_reset(ttytail);
}

static void ttytail_rx_timestamp(struct ttytail *ttytail, uint8_t first)
{
	union {
		uint8_t bytes[5];
		uint64_t qword;
	} u;
	unsigned long long timestamp;
	struct sk_buff *skb;
	int err;

	u.qword = 0;
	u.bytes[0] = first;
	err = ttytail_rx_bytes(ttytail, &u.bytes[1], (sizeof(u.bytes) - 1));
	if (err) {
		dev_err(ttytail->dev, "invalid timestamp\n");
		goto drop;
	}

	timestamp = le64_to_cpu(u.qword);

	ttytail_rx_reset(ttytail);

	if (ttytail->rx.skb) {
		dev_info(ttytail->dev, "RX time %llx\n", timestamp);
		skb = ttytail->rx.skb;
		ttytail->rx.skb = NULL;
		wmb();
		ieee802154_rx_irqsafe(ttytail->hw, skb, 0);
	} else if (ttytail->tx.skb) {
		dev_info(ttytail->dev, "TX time %llx\n", timestamp);
		skb = ttytail->tx.skb;
		ttytail->tx.skb = NULL;
		wmb();
		ieee802154_xmit_complete(ttytail->hw, skb, false);
	} else {
		dev_err(ttytail->dev, "stray timestamp %llx\n", timestamp);
	}

	return;

 drop:
	ttytail_rx_reset(ttytail);
}

static void ttytail_rx_config(struct ttytail *ttytail, char *key)
{
	union {
		uint8_t bytes[8];
		uint64_t eui64;
	} u;
	int err;

	if (strcmp(key, "eui") == 0) {
		err = ttytail_rx_bytes(ttytail, u.bytes, sizeof(u.bytes));
		if (err) {
			dev_err(ttytail->dev, "invalid EUI-64\n");
			goto err;
		}
		ttytail->eui64 = u.eui64;
	} else {
		dev_err(ttytail->dev, "unknown config key \"%s\"\n", key);
	}

 err:
	ttytail_rx_reset(ttytail);
}

static void ttytail_rx(struct ttytail *ttytail)
{
	struct ttytail_line *line = &ttytail->rx.line;
	char *sep;
	int len;

	dev_info(ttytail->dev, "< %s", line->data);

	len = ttytail_rx_byte(ttytail);
	if (len >= 0) {
		if ((line->data[line->offset] == ':') &&
		    (line->data[line->offset + 1] == ' ')) {
			line->offset += 2;
			ttytail_rx_packet(ttytail, len);
		} else if (line->data[line->offset] == ' ') {
			ttytail_rx_timestamp(ttytail, len);
		} else {
			dev_err(ttytail->dev, "invalid data line \"%s\"\n",
				line->data);
			ttytail_rx_reset(ttytail);
		}
	} else if ((sep = strchr(line->data, ':')) != NULL) {
		*sep++ = '\0';
		line->offset = (sep - line->data);
		ttytail_rx_config(ttytail, line->data);
		ttytail_rx_reset(ttytail);
	} else {
		dev_err(ttytail->dev, "invalid line \"%s\"\n", line->data);
		ttytail_rx_reset(ttytail);
	}
}

/*****************************************************************************
 *
 * IEEE 802.15.4 interface
 *
 */

static int ttytail_start(struct ieee802154_hw *hw)
{
	struct ttytail *ttytail = hw->priv;

	dev_info(ttytail->dev, "started\n");
	return 0;
}

static void ttytail_stop(struct ieee802154_hw *hw)
{
	struct ttytail *ttytail = hw->priv;

	ttytail_tx_cancel(ttytail);
	dev_info(ttytail->dev, "stopped\n");
}

static int ttytail_ed(struct ieee802154_hw *hw, u8 *level)
{
	struct ttytail *ttytail = hw->priv;

	dev_info(ttytail->dev, "detecting energy\n");
	*level = 0;
	return 0;
}

static int ttytail_set_channel(struct ieee802154_hw *hw, u8 page, u8 channel)
{
	struct ttytail *ttytail = hw->priv;

	dev_info(ttytail->dev, "setting channel %d:%d\n", page, channel);
	return 0;
}

static int ttytail_xmit_async(struct ieee802154_hw *hw, struct sk_buff *skb)
{
	struct ttytail *ttytail = hw->priv;
	struct ttytail_line *line = &ttytail->tx.line;
	uint8_t *bytes;
	char *buf;
	size_t len;
	size_t i;

	if (ttytail->tx.skb) {
		dev_err(ttytail->dev, "concurrent transmission attempted\n");
		return -ENOBUFS;
	}
	if (skb_is_nonlinear(skb)) {
		dev_err(ttytail->dev, "nonlinear transmission attempted\n");
		return -ENOTSUPP;
	}

	len = (3 /* "tx" */ + skb->len * 3 /* " XX" */ + 2 /* "\r\n" */ +
	       1 /* NUL */);
	if (len > sizeof(line->data)) {
		dev_err(ttytail->dev, "overlength transmission attempted\n");
		return -EINVAL;
	}

	bytes = skb->data;
	buf = line->data;
	buf += sprintf(buf, "tx");
	for (i = 0; i < skb->len; i++)
		buf += sprintf(buf, " %x", *bytes++);
	buf += sprintf(buf, "\r\n");

	ttytail->tx.skb = skb;
	ttytail_tx_start(ttytail, NULL);
	return 0;
}

static const struct ieee802154_ops ttytail_ops = {
	.owner = THIS_MODULE,
	.start = ttytail_start,
	.stop = ttytail_stop,
	.xmit_async = ttytail_xmit_async,
	.ed = ttytail_ed,
	.set_channel = ttytail_set_channel,
};

/*****************************************************************************
 *
 * TTY line discipline
 *
 */

static int ttytail_open(struct tty_struct *tty)
{
	struct ieee802154_hw *hw;
	struct ttytail *ttytail;
	int err;

	if (!capable(CAP_NET_ADMIN)) {
		err = -EPERM;
		goto err_capable;
	}

	if (tty->ops->write == NULL) {
		err = -EOPNOTSUPP;
		goto err_readonly;
	}

	hw = ieee802154_alloc_hw(sizeof(*ttytail), &ttytail_ops);
	if (!hw) {
		err = -ENOMEM;
		goto err_alloc_hw;
	}
	ttytail = hw->priv;
	memset(ttytail, 0, sizeof(*ttytail));
	ttytail->hw = hw;
	ttytail->tty = tty;
	ttytail->dev = &ttytail->hw->phy->dev;
	INIT_WORK(&ttytail->tx.work, ttytail_tx_worker);
	init_waitqueue_head(&ttytail->tx.wait);

	hw->extra_tx_headroom = 0;
	hw->parent = ttytail->tty->dev;
	hw->flags = IEEE802154_HW_OMIT_CKSUM;

	tty->disc_data = ttytail;

	ttytail_tx_start(ttytail, TTYTAIL_INIT);
	ttytail_tx_wait(ttytail);

	err = ieee802154_register_hw(ttytail->hw);
	if (err) {
		dev_err(ttytail->dev, "could not register: %d\n", err);
		goto err_register;
	}

	dev_info(ttytail->dev, "registered on %s\n",
		 dev_name(ttytail->tty->dev));
	return 0;

	ieee802154_unregister_hw(ttytail->hw);
 err_register:
	ttytail_tx_cancel(ttytail);
	ttytail_tx_start(ttytail, TTYTAIL_RESET);
	ttytail_tx_wait(ttytail);
	ttytail_tx_cancel(ttytail);
	ttytail_rx_reset(ttytail);
	tty->disc_data = NULL;
	ieee802154_free_hw(ttytail->hw);
 err_alloc_hw:
 err_readonly:
 err_capable:
	return err;
}

static void ttytail_close(struct tty_struct *tty)
{
	struct ttytail *ttytail = tty->disc_data;

	ieee802154_unregister_hw(ttytail->hw);
	ttytail_tx_cancel(ttytail);
	ttytail_tx_start(ttytail, TTYTAIL_RESET);
	ttytail_tx_wait(ttytail);
	ttytail_tx_cancel(ttytail);
	ttytail_rx_reset(ttytail);
	tty->disc_data = NULL;
	ieee802154_free_hw(ttytail->hw);
}

static int ttytail_receive_buf2(struct tty_struct *tty,
				const unsigned char *data,
				char *flags, int count)
{
	struct ttytail *ttytail = tty->disc_data;
	int remaining;

	for (remaining = count; remaining; remaining--, data++) {
		if ((*data == '\r') || (*data == '\n')) {
			if (ttytail->rx.line.len)
				ttytail_rx(ttytail);
		} else if (ttytail->rx.line.len <
			   (sizeof(ttytail->rx.line.data) - 1 /* NUL */)) {
			ttytail->rx.line.data[ttytail->rx.line.len++] = *data;
		}
	}
	return count;
}

static void ttytail_write_wakeup(struct tty_struct *tty)
{
	struct ttytail *ttytail = tty->disc_data;

	schedule_work(&ttytail->tx.work);
}

static struct tty_ldisc_ops ttytail_ldisc = {
	.magic = TTY_LDISC_MAGIC,
	.owner = THIS_MODULE,
	.name = "ttytail",
	.open = ttytail_open,
	.close = ttytail_close,
	.receive_buf2 = ttytail_receive_buf2,
	.write_wakeup = ttytail_write_wakeup,
};

/*****************************************************************************
 *
 * Module interface
 *
 */

static int __init ttytail_init(void)
{
	int err;

	err = tty_register_ldisc(X_N_TAIL, &ttytail_ldisc);
	if (err != 0) {
		printk(KERN_ERR "ttytail: cannot register line discipline: "
		       "error %d\n", err);
		goto err_register_ldisc;
	}
	printk(KERN_INFO "ttytail: registered as line discipline %d\n",
	       X_N_TAIL);

	return 0;

	tty_unregister_ldisc(X_N_TAIL);
 err_register_ldisc:
	return err;
}

static void __exit ttytail_exit(void)
{
	tty_unregister_ldisc(X_N_TAIL);
}

module_init(ttytail_init);
module_exit(ttytail_exit);
MODULE_AUTHOR("Michael Brown <mbrown@fensystems.co.uk>");
MODULE_DESCRIPTION("IEEE 802.15.4 TTY-based Tail driver");
MODULE_LICENSE("GPL");
MODULE_ALIAS_LDISC(X_N_TAIL);
