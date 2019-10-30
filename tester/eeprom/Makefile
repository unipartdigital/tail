DTC		= dtc

EEPROMUTILS	= hats/eepromutils
EEPMAKE		= $(EEPROMUTILS)/eepmake
EEPDUMP		= $(EEPROMUTILS)/eepdump

.PHONY : all tools clean

all : tools tailtest.dtbo tailtest.eep tailtest_dut.dtbo

%.dtbo : %.dts Makefile
	$(DTC) -@ -I dts -O dtb -o $@ $<

%.dtso : %.dtbo
	$(DTC) -@ -I dtb -O dts -o $@ $<

%.eep : %.dtbo tailtest.txt $(EEPMAKE)
	$(EEPMAKE) tailtest.txt $@ $<

%.dump : %.eep $(EEPDUMP)
	$(EEPDUMP) $< $@

tools : $(EEPMAKE) $(EEPDUMP)

$(EEPMAKE) $(EEPDUMP) :
	$(MAKE) -C $(EEPROMUTILS)

clean :
	$(RM) *.dtbo *.dtso *.eep *.dump
	$(MAKE) -C $(EEPROMUTILS) clean
