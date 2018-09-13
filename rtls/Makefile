#
# Makefile for Tail RTLS
#

all:
	@echo "Nothing for now."

locate:
	./loctest.py magpi1 bss1 bss2 bss3 bss4 bss5 bss6 bss7 bss8 --raw --rate 850 --txpsr 1024 --smart_power 0 --tx_power 3+5


myday:
	./delay.py bss1 bss2 --raw --count 1000 --plot --range 5.0 --rate 850 --txpsr 1024 --smart_power 0 --tx_power 3+8

clean:
	rm -fr __pycache__
	rm -f *~

