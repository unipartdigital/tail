##
## Makefile for Tail software
##

## Config

ANCHOR_ROOT ?= /netboot/buster

FILES := \
	anchord.py		\
	anchor.service		\
	blinks.py		\
	dwarf.py		\
	tail.py			\
	ranging.py		\
	xtaltrim.py		\
	calibrate.py		\
	setup4-11-14.json	\
	setup4-1-4.json		\
	setup4-5-8.json		\
	setup.json		\
	calib.json		\
	modhat			\


## Rules

.PHONY: all install-anchor install-testserver

all:
	@echo "all done!"

install-anchor:
	install -o root -g root -m 755 anchord.py $(ANCHOR_ROOT)/sbin/anchord
	install -o root -g root -m 644 tail.py dwarf.py blinks.py $(ANCHOR_ROOT)/usr/lib/python3.7/
	install -o root -g root -m 644 anchor.service $(ANCHOR_ROOT)/lib/systemd/system/

install-testserver:
	scp -4 $(FILES) pmattila@testserver:~/Projects/Tail/calib/

install-server-host:
	scp -J testserver.example.com $(FILES) pmattila@server-host:~/Projects/Tail/calib/

install-magpi0:
	scp -J testserver.example.com $(FILES) root@magpi0:/root/calib/


clean:
	rm -fr __pycache__
	rm -f *~

