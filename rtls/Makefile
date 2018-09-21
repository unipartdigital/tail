#
# Makefile for Tail RTLS
#

DATE=$(shell date +%Y-%m-%d)

COMMA=,
EMPTY=#
SPACE=$(EMPTY) $(EMPTY)

STEPS := 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15

POWER3 = $(foreach P,$(STEPS),3+$P)
POWER6 = $(foreach P,$(STEPS),6+$P)
POWER9 = $(foreach P,$(STEPS),9+$P)

POWERS := $(POWER3) $(POWER6) $(POWER9)
POWERS := $(subst $(SPACE),$(COMMA),$(POWERS))


all:
	@echo "Nothing for now."

locate:
	./loctest.py magpi1* bss1 bss2 bss3 bss4 bss5 bss6 bss7 bss8 --raw --rate 850 --txpsr 1024 --smart_power 0 --tx_power 3+8

dataset:
	./twrtest.py bss1:bss2 bss1:bss4 bss2:bss3 bss3:bss4 bss5:bss6 bss5:bss7 bss5:bss8 bss6:bss7 bss6:bss8 bss7:bss8 -P $(POWERS) -s 10 -R -o DATA/TWR-$(DATE).csv

myday:
	./delay.py bss1 bss2 --raw --count 1000 --plot --range 5.0 --rate 850 --txpsr 1024 --smart_power 0 --tx_power 3+8

clean:
	rm -fr __pycache__
	rm -f *~

