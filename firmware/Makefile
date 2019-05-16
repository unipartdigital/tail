# Copyright (C) 2019 Luke Barone-Adesi <luke.barone-adesi@unipart.io>
# License: whatever is being used for Tail

# Background:
# Automatically track dependencies without a separate depend target:
# http://make.mad-scientist.net/papers/advanced-auto-dependency-generation/

# Recursive make considered harmful:
# http://lcgapp.cern.ch/project/architecture/recursive_make.pdf
# Modernised example:
# https://www.oreilly.com/library/view/managing-projects-with/0596006101/ch06.html

all: bootloader.axf

CC = arm-none-eabi-gcc
TARGET_ARCH = -mcpu=cortex-m0plus -mthumb
DEBUG_FLAGS += -g3 -gdwarf-2
CFLAGS += $(DEBUG_FLAGS)
CFLAGS += $(TARGET_ARCH)
CFLAGS += -std=c99 -DEFM32HG222F64=1 -DNDEBUG=1
CFLAGS += -O3 -Wall -fmessage-length=0 -ffunction-sections -fdata-sections

LDFLAGS += -T "Tail.ld" -Xlinker --gc-sections -Xlinker -Map="Tail.map" --specs=nano.specs
SYSLIBS = -Wl,--start-group -lgcc -lc -lnosys -Wl,--end-group # TODO rename?

INCDIR_BASE = $(CURDIR)/efm32-base
INCDIRS = $(INCDIR_BASE)/emlib/inc
INCDIRS += $(INCDIR_BASE)/device/EFM32HG/Include
INCDIRS += $(INCDIR_BASE)/cmsis/Include
CFLAGS += $(patsubst %,-I%,$(INCDIRS))

MODULES := emlib src CMSIS/EFM32HG bootloader_src
SRCS :=
include $(patsubst %,%/module.mk,$(MODULES))

BUILDDIR := .build
$(shell mkdir -p $(BUILDDIR) >/dev/null)
TAIL_OBJECTS := $(patsubst %.c,$(BUILDDIR)/%.o,$(SRCS))
BOOTLOADER_OBJECTS := $(patsubst %.c,$(BUILDDIR)/%.o,$(BOOTLOADER_SRCS))

DEPDIR := $(BUILDDIR)/.d
$(shell mkdir -p $(DEPDIR) >/dev/null)

SUBDEPDIRS := $(foreach MB,$(MODULES),$(shell find $(MB) -type d))
$(foreach sdd,$(SUBDEPDIRS),$(shell mkdir -p $(BUILDDIR)/$(sdd) >/dev/null))
$(foreach sdd,$(SUBDEPDIRS),$(shell mkdir -p $(DEPDIR)/$(sdd) >/dev/null))
DEPFLAGS = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td

COMPILE.c = $(CC) $(DEPFLAGS) $(CFLAGS) -c
POSTCOMPILE = @mv -f $(DEPDIR)/$*.Td $(DEPDIR)/$*.d && touch $@

# FIXME: layer cmsis builds more cleanly
CMSIS_EFM32HG_ASM_FLAGS := -c -x assembler-with-cpp
$(BUILDDIR)/$(CMSIS_EFM32HG_SRC_DIRNAME)/%.o: $(CMSIS_EFM32HG_SRC_DIRNAME)/%.s
	$(CC) $(TARGET_ARCH) $(CMSIS_EFM32HG_ASM_FLAGS) $(OUTPUT_OPTION) $<

CMSIS_EFM32HG_CFLAGS += -O0 -Wall -fmessage-length=0 -mno-sched-prolog \
    -fno-builtin -ffunction-sections -fdata-sections
$(BUILDDIR)/$(CMSIS_EFM32HG_SRC_DIRNAME)/%.o: $(CMSIS_EFM32HG_SRC_DIRNAME)/%.c
	$(CC) $(DEPFLAGS) $(CFLAGS) $(CMSIS_EFM32HG_CFLAGS) $(OUTPUT_OPTION) -c $<
	$(POSTCOMPILE)

%.o : $.c
$(BUILDDIR)/%.o : %.c $(DEPDIR)/%.d
	$(COMPILE.c) $(OUTPUT_OPTION) $<
	$(POSTCOMPILE)

$(DEPDIR)/%.d: ;
.PRECIOUS: $(DEPDIR)/%.d

include $(wildcard $(patsubst %,$(DEPDIR)/%.d,$(basename $(SRCS))))

CMSIS_OBJECTS = $(BUILDDIR)/CMSIS/EFM32HG/startup_gcc_efm32hg.o \
                $(BUILDDIR)/CMSIS/EFM32HG/system_efm32hg.o

Tail.axf: $(TAIL_OBJECTS) $(CMSIS_OBJECTS)
	$(CC) $(DEBUG_FLAGS) $(TARGET_ARCH) $(LDFLAGS) -o Tail.axf $(CMSIS_OBJECTS) $(TAIL_OBJECTS) $(SYSLIBS)

	arm-none-eabi-objcopy -O ihex "Tail.axf" "Tail.hex"
	arm-none-eabi-objcopy -O binary "Tail.axf" "Tail.bin"
	arm-none-eabi-objcopy -O srec "Tail.axf" "Tail.s37"
	arm-none-eabi-size "Tail.axf"

bootloader.axf: $(BOOTLOADER_OBJECTS) $(CMSIS_OBJECTS)
	$(CC) $(DEBUG_FLAGS) $(TARGET_ARCH) $(LDFLAGS) -o bootloader.axf $(CMSIS_OBJECTS) $(BOOTLOADER_OBJECTS) $(SYSLIBS)

	arm-none-eabi-objcopy -O ihex "bootloader.axf" "bootloader.hex"
	arm-none-eabi-objcopy -O binary "bootloader.axf" "bootloader.bin"
	arm-none-eabi-objcopy -O srec "bootloader.axf" "bootloader.s37"
	arm-none-eabi-size "bootloader.axf"

# TODO: make this more defensive
clean:
	rm -rf $(DEPDIR) $(BUILDDIR)
	rm -f [Tb]*.axf [Tb]*.hex [Tb]*.bin [Tb]*.s37 [Tb]*.map

.PHONY: all clean
