##
## Makefile for Tail Demo software
##

## Config

ANCHOR_ROOT ?= /netboot/buster


## Rules

.PHONY: all install-server install-anchor install-client install-testserver

all:
	@echo "all done!"

install-anchor:
	install -o root -g root -m 644 config.json $(ANCHOR_ROOT)/etc/tail.json
	install -o root -g root -m 755 tagemu.py $(ANCHOR_ROOT)/sbin/tagemu
	install -o root -g root -m 755 anchord.py $(ANCHOR_ROOT)/sbin/anchord
	install -o root -g root -m 644 tail.py dwarf.py tdoa.py	$(ANCHOR_ROOT)/usr/lib/python3.7/
	install -o root -g root -m 644 anchor.service $(ANCHOR_ROOT)/lib/systemd/system/

install-server:
	install -o root -g root -m 644 config.json $(INSTALL_ROOT)/etc/tail.json
	install -o root -g root -m 755 rtlsd.py $(INSTALL_ROOT)/sbin/rtlsd
	install -o root -g root -m 644 tail.py dwarf.py tdoa.py	$(INSTALL_ROOT)/usr/lib/python3.7/site-packages/
	install -o root -g root -m 644 rtls.service $(INSTALL_ROOT)/lib/systemd/system/

install-client:
	install -o root -g root -m 644 config.json $(INSTALL_ROOT)/etc/tail.json
	install -o root -g root -m 644 tail.py dwarf.py tdoa.py	$(INSTALL_ROOT)/usr/lib/python3.7/site-packages/
	install -o root -g root -m 755 demoroom.py $(INSTALL_ROOT)/bin/demoroom

install-testserver:
	scp *.py *.json *.service Makefile pmattila@testserver:~/Projects/Tail/demo/


clean:
	rm -fr __pycache__
	rm -f *~
