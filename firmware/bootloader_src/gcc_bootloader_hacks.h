#ifndef _GCC_BOOTLOADER_HACKS_H
#define _GCC_BOOTLOADER_HACKS_H
#define __ramfunc __attribute__ ((long_call, section(".ram")))
#define __no_init
#define __noreturn __attribute__((noreturn))

#endif /* _GCC_BOOTLOADER_HACKS_H */
