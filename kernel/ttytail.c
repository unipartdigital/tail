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

static void ttytail_tx(struct work_struct *work)
{
	struct ttytail *ttytail = container_of(work, struct ttytail, tx_work);

	(void) ttytail;
}

static int ttytail_start(struct ieee802154_hw *hw)
{
	struct ttytail *ttytail = hw->priv;

	dev_info(ttytail->dev, "started\n");
	return 0;
}

static void ttytail_stop(struct ieee802154_hw *hw)
{
	struct ttytail *ttytail = hw->priv;

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

	dev_info(ttytail->dev, "transmitting\n");
	ieee802154_xmit_complete(hw, skb, false);
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

static int ttytail_open(struct tty_struct *tty)
{
	struct ieee802154_hw *hw;
	struct ttytail *ttytail;
	int ret;

	if (!capable(CAP_NET_ADMIN))
		return -EPERM;

	if (tty->ops->write == NULL)
		return -EOPNOTSUPP;

	hw = ieee802154_alloc_hw(sizeof(*ttytail), &ttytail_ops);
	if (!hw) {
		ret = -ENOMEM;
		goto err_alloc;
	}
	ttytail = hw->priv;
	ttytail->hw = hw;
	ttytail->tty = tty;
	ttytail->dev = &ttytail->hw->phy->dev;
	INIT_WORK(&ttytail->tx_work, ttytail_tx);

	hw->extra_tx_headroom = 0;
	hw->parent = ttytail->tty->dev;
	hw->flags = IEEE802154_HW_OMIT_CKSUM;

	tty->disc_data = ttytail;

	ret = ieee802154_register_hw(ttytail->hw);
	if (ret)
		goto err_register_hw;

	dev_info(ttytail->dev, "registered on %s\n",
		 dev_name(ttytail->tty->dev));
	return 0;

	flush_work(&ttytail->tx_work);
	ieee802154_unregister_hw(ttytail->hw);
 err_register_hw:
	tty->disc_data = NULL;
	ieee802154_free_hw(ttytail->hw);
 err_alloc:
	return ret;
}

static void ttytail_close(struct tty_struct *tty)
{
	struct ttytail *ttytail = tty->disc_data;

	flush_work(&ttytail->tx_work);
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

	schedule_work(&ttytail->tx_work);
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

static int __init ttytail_init(void)
{
	int ret;

	ret = tty_register_ldisc(X_N_TAIL, &ttytail_ldisc);
	if (ret != 0) {
		printk(KERN_ERR "ttytail: cannot register line discipline: "
		       "error %d\n", ret);
		goto err_register_ldisc;
	}

	return 0;

	tty_unregister_ldisc(X_N_TAIL);
 err_register_ldisc:
	return ret;
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
