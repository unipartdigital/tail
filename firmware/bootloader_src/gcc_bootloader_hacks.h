#ifndef _GCC_BOOTLOADER_HACKS_H
#define _GCC_BOOTLOADER_HACKS_H
/*#define __ramfunc __attribute__ ((longcall, section(".data")))*/
#define __ramfunc __attribute__ ((section(".data")))
#define __no_init  __attribute__ ((section (".noinit")))
#define __noreturn __attribute__((noreturn))

#endif /* _GCC_BOOTLOADER_HACKS_H */
