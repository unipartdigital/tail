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

/*****************************************************************************
 *
 * Transmit datapath
 *
 */

static void ttytail_tx_worker(struct work_struct *work)
{
	struct ttytail *ttytail = container_of(work, struct ttytail, tx.work);
	void (*complete)(struct ttytail *ttytail, int err);
	char *data;
	size_t remaining;
	size_t actual;

	remaining = (ttytail->tx.line.len - ttytail->tx.line.offset);
	if (remaining) {
		data = &ttytail->tx.line.data[ttytail->tx.line.offset];
		actual = ttytail->tty->ops->write(ttytail->tty, data,
						  remaining);
		ttytail->tx.line.offset += actual;
		if (actual == remaining) {
			complete = ttytail->tx.complete;
			ttytail->tx.complete = NULL;
			complete(ttytail, 0);
		}
	}
}

static void ttytail_tx_start(struct ttytail *ttytail,
			     void (*complete)(struct ttytail *ttytail, int err),
			     const char *fmt, ...)
{
	va_list args;

	WARN_ON(ttytail->tx.complete != NULL);

	va_start(args, fmt);
	if (fmt) {
		vsnprintf(ttytail->tx.line.data, sizeof(ttytail->tx.line.data),
			  fmt, args);
	}
	va_end(args);
	dev_info(ttytail->dev, "> %s", ttytail->tx.line.data);

	ttytail->tx.line.offset = 0;
	ttytail->tx.line.len = strlen(ttytail->tx.line.data);
	ttytail->tx.complete = complete;

	schedule_work(&ttytail->tx.work);
}

static void ttytail_tx_cancel(struct ttytail *ttytail)
{
	void (*complete)(struct ttytail *ttytail, int err);

	cancel_work_sync(&ttytail->tx.work);
	if (ttytail->tx.complete) {
		complete = ttytail->tx.complete;
		ttytail->tx.complete = NULL;
		complete(ttytail, -ECANCELED);
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

static void ttytail_xmit_complete(struct ttytail *ttytail, int err)
{
	struct sk_buff *skb;

	skb = ttytail->tx.skb;
	ttytail->tx.skb = NULL;
	wmb();
	ieee802154_xmit_complete(ttytail->hw, skb, false);
}

static int ttytail_xmit_async(struct ieee802154_hw *hw, struct sk_buff *skb)
{
	struct ttytail *ttytail = hw->priv;
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

	len = (3 /* "tx" */ + skb->len * 3 /* " XX" */ + 1 /* "\n" */ +
	       1 /* NUL */);
	if (len > sizeof(ttytail->tx.line.data)) {
		dev_err(ttytail->dev, "overlength transmission attempted\n");
		return -EINVAL;
	}

	bytes = skb->data;
	buf = ttytail->tx.line.data;
	buf += sprintf(buf, "tx");
	for (i = 0; i < skb->len; i++)
		buf += sprintf(buf, " %x", *bytes++);
	buf += sprintf(buf, "\n");

	ttytail_tx_start(ttytail, ttytail_xmit_complete, NULL);
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

static void ttytail_open_complete(struct ttytail *ttytail, int err)
{

	if (err)
		return;

	err = ieee802154_register_hw(ttytail->hw);
	if (err) {
		dev_err(ttytail->dev, "could not register: %d\n", err);
		return;
	}

	ttytail->registered = true;
	dev_info(ttytail->dev, "registered on %s\n",
		 dev_name(ttytail->tty->dev));
}

static int ttytail_open(struct tty_struct *tty)
{
	struct ieee802154_hw *hw;
	struct ttytail *ttytail;

	if (!capable(CAP_NET_ADMIN))
		return -EPERM;

	if (tty->ops->write == NULL)
		return -EOPNOTSUPP;

	hw = ieee802154_alloc_hw(sizeof(*ttytail), &ttytail_ops);
	if (!hw)
		return -ENOMEM;
	ttytail = hw->priv;
	memset(ttytail, 0, sizeof(*ttytail));
	ttytail->hw = hw;
	ttytail->tty = tty;
	ttytail->dev = &ttytail->hw->phy->dev;
	INIT_WORK(&ttytail->tx.work, ttytail_tx_worker);

	hw->extra_tx_headroom = 0;
	hw->parent = ttytail->tty->dev;
	hw->flags = IEEE802154_HW_OMIT_CKSUM;

	tty->disc_data = ttytail;

	ttytail_tx_start(ttytail, ttytail_open_complete, "echo 0\n");
	return 0;
}

static void ttytail_close(struct tty_struct *tty)
{
	struct ttytail *ttytail = tty->disc_data;

	ttytail_tx_cancel(ttytail);
	if (ttytail->registered)
		ieee802154_unregister_hw(ttytail->hw);
	tty->disc_data = NULL;
	ieee802154_free_hw(ttytail->hw);
}

static int ttytail_receive_buf2(struct tty_struct *tty,
				const unsigned char *data,
				char *flags, int count)
{
	struct ttytail *ttytail = tty->disc_data;

	dev_info(ttytail->dev, "received %d bytes\n", count);
	return 0;
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
