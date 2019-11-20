##
## Makefile for Tail software
##

## Config

ANCHOR_ROOT ?= /netboot/buster


## Rules

.PHONY: all install-anchor install-fluffy

all:
	@echo "all done!"

install-anchor:
	install -o root -g root -m 755 anchord.py $(ANCHOR_ROOT)/sbin/anchord
	install -o root -g root -m 644 tail.py dwarf.py blinks.py $(ANCHOR_ROOT)/usr/lib/python3.7/
	install -o root -g root -m 644 anchor.service $(ANCHOR_ROOT)/lib/systemd/system/

install-fluffy:
	scp -4 *.py *.sh *.json *.service pmattila@fluffy:~/Projects/Tail/calib/

install-resistor:
	scp -6 *.py *.sh *.json *.service pmattila@resistor:~/Projects/Tail/calib/


clean:
	rm -fr __pycache__
	rm -f *~

