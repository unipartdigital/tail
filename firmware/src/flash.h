/* flash.h */

#ifndef _FLASH_H
#define _FLASH_H

void flash_write(void *addr, void *data, int len);
void flash_erase(void *addr, int size);

#endif
