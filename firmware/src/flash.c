/* flash.c */

#include "flash.h"
#include "em_device.h"
#include "em_msc.h"

void flash_write(void *addr, void *data, int len)
{
	MSC_Init();
	MSC_WriteWord(addr, data, len & ~3);
	if (len & 3) {
		uint8_t b[4] = {0xff, 0xff, 0xff, 0xff};
		memcpy(b, data + (len & ~3), len);
		MSC_WriteWord(addr + (len & ~3), b, 4);
	}
	MSC_Deinit();
}

void flash_erase(void *addr, int size)
{
	MSC_Init();
	if ((((uint32_t)addr) & (FLASH_PAGE_SIZE-1)) != 0)
			for (;;) ;
	for (int i = 0; i < size; i+= FLASH_PAGE_SIZE)
	    MSC_ErasePage(addr+i);
	MSC_Deinit();
}
