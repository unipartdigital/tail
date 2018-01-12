/* config.c */

#include <stdbool.h>
#include <string.h>

#include "common.h"

#include "config.h"
#include "flash.h"

uint8_t *config_area;

#define CONFIG_FLASH_TOP 0x10000

#define CONFIG_FLASH_START (CONFIG_FLASH_TOP - CONFIG_AREA_SIZE*2)

#define CONFIG_AREA1 (void *)CONFIG_FLASH_START
#define CONFIG_AREA2 (void *)(CONFIG_FLASH_START + CONFIG_AREA_SIZE)

/* Size of magic */
#define CONFIG_AREA_MAGIC 0x37427411UL
#define CONFIG_AREA_OFFSET 4
#define CONFIG_AREA_SIZE 1024

#define CONFIG_KEY(offset) (config_area[offset] + (config_area[offset+1] << 8))
#define CONFIG_LENGTH(offset) (config_area[offset+2])
#define CONFIG_SPARE(offset) (config_area[offset+3])
#define CONFIG_HEADER_SIZE 4

#define CONFIG_ALIGN(x) (((x)+3)&~3)

#define CONFIG_TOTLEN(x) (CONFIG_ALIGN(CONFIG_LENGTH(x)) + CONFIG_HEADER_SIZE)

#define CONFIG_KEY_UNPROGRAMMED 0xffff

typedef struct {
	config_key key;
	const char *name;
} config_key_entry;

#define X(name, num) { num, #name },
const config_key_entry config_key_table[] = {
		CONFIG_KEYS
};
#undef X

int config_findfree(void);
void config_compact(void);

bool config_valid(uint8_t *addr)
{
    if (*(uint32_t *)addr != CONFIG_AREA_MAGIC)
    	return false;

    config_area = addr;

   	int offset;
   	for (offset = CONFIG_AREA_OFFSET; offset < CONFIG_AREA_SIZE; offset += CONFIG_TOTLEN(offset)) {
   		if (offset >= (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE))
   			return false;
       	if (CONFIG_KEY(offset) == CONFIG_KEY_UNPROGRAMMED)
            return true;
   	}

   	return false;
}

bool config_freespacevalid(void)
{
	int offset = config_findfree();
	if (offset < 0)
		return false; // full or invalid free space

	for (; offset < CONFIG_AREA_SIZE; offset++)
		if (config_area[offset] != 0xff)
			return false;

	return true;
}

bool config_empty(uint8_t *addr)
{
	int offset;
	for (offset = 0; offset < CONFIG_AREA_SIZE; offset++)
		if (config_area[offset] != 0xff)
			return false;

	return true;
}

void config_init_area(uint8_t *addr)
{
	uint32_t magic = CONFIG_AREA_MAGIC;
	flash_write(addr, &magic, 4);
}

void config_init(void)
{
	bool valid1 = config_valid(CONFIG_AREA1);
	bool valid2 = config_valid(CONFIG_AREA2);
	if (!(valid1 || valid2)) {
		flash_erase(CONFIG_AREA1, CONFIG_AREA_SIZE);
		config_init_area(CONFIG_AREA1);
		config_area = CONFIG_AREA1;
		return;
	}
	if (valid1 && !valid2) {
		config_area = CONFIG_AREA1;
		return;
	}
	if (valid2 && !valid1) {
		config_area = CONFIG_AREA2;
		return;
	}

	/* Both are valid. We need to choose one. This probably
	 * means that we lost power during compacting. Therefore
	 * the one with the least free space probably has all
	 * the data that we care about. Start the compaction again
	 * next time we try to write.
	 */

	int free1, free2;

	config_area = CONFIG_AREA1;
	free1 = config_findfree();
	config_area = CONFIG_AREA2;
	free2 = config_findfree();

	if (free1 >= free2) {
		config_area = CONFIG_AREA1;
		flash_erase(CONFIG_AREA2, CONFIG_AREA_SIZE);
	} else {
		config_area = CONFIG_AREA2; // Stricly redundant, but much less error-prone here
		flash_erase(CONFIG_AREA1, CONFIG_AREA_SIZE);
	}
	if (!config_freespacevalid())
		config_compact();
}

void config_compact(void)
{
	int offset, new_offset;
	uint8_t *new_area;
	uint32_t null = 0;
	if (config_area == CONFIG_AREA1)
		new_area = CONFIG_AREA2;
	else
		new_area = CONFIG_AREA1;
	if (!config_empty(new_area))
		flash_erase(new_area, CONFIG_AREA_SIZE);

	config_init_area(new_area);

	new_offset = CONFIG_AREA_OFFSET;
    for (offset = CONFIG_AREA_OFFSET; (offset < (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE)) && (CONFIG_KEY(offset) != CONFIG_KEY_UNPROGRAMMED); offset += CONFIG_TOTLEN(offset))
    	if (CONFIG_KEY(offset) != 0) {
    		flash_write(new_area + new_offset, config_area + offset, CONFIG_TOTLEN(offset));
    		new_offset += CONFIG_TOTLEN(offset);
    	}

    flash_write(config_area, &null, 4);
    config_area = new_area;
}

int config_find(config_key key)
{
	int offset;
	for (offset = CONFIG_AREA_OFFSET; (offset < (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE)) && (CONFIG_KEY(offset) != CONFIG_KEY_UNPROGRAMMED); offset += CONFIG_TOTLEN(offset))
		if (CONFIG_KEY(offset) == key)
			return offset;
	return -1;
}

int config_findfree(void)
{
	int offset;
	for (offset = CONFIG_AREA_OFFSET; offset < (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE); offset += CONFIG_TOTLEN(offset))
        if (CONFIG_KEY(offset) == CONFIG_KEY_UNPROGRAMMED)
		    return offset;
	return -1;
}

int config_len(config_key key)
{
	int offset = config_find(key);
	if (offset < 0)
		return -1;
	return CONFIG_LENGTH(offset);
}

int config_get(config_key key, uint8_t *data, int maxlen)
{
	int offset = config_find(key);
	if (offset < 0)
		return -1;
	int len = CONFIG_LENGTH(offset);
	if (len > maxlen)
		len = maxlen;
	memcpy(data, config_area+offset+CONFIG_HEADER_SIZE, len);
	return len;
}

#define CONFIG_SPACE_FOR_KEY(offset, len) ((offset >= 0) && (offset < (CONFIG_AREA_SIZE - CONFIG_TOTLEN(len)) - CONFIG_HEADER_SIZE))
bool config_put(config_key key, uint8_t *data, int len)
{
	int offset;
	uint8_t header[CONFIG_HEADER_SIZE];

	if (len > 0xff)
		return false;

	offset = config_find(key);
	if (offset >= 0) {
		if (CONFIG_LENGTH(offset) == len) {
			int i;
			for (i = 0; i < len; i++)
				if (config_area[offset + CONFIG_HEADER_SIZE + i] != data[i])
					break;
			if (i == len)
				return true; // Data is identical to current contents
		}
	}

	config_delete(key);
	offset = config_findfree();
	if (!CONFIG_SPACE_FOR_KEY(offset, len)) {
		config_compact();
		offset = config_findfree();
		if (!CONFIG_SPACE_FOR_KEY(offset, len))
			return false;
	}

	flash_write(config_area + offset + CONFIG_HEADER_SIZE, data, len);
	header[0] = key & 0xff;
	header[1] = (key >> 8) & 0xff;
	header[2] = len;
	header[3] = 0xff; // Spare, for now
	flash_write(config_area + offset, header, CONFIG_HEADER_SIZE);

	return true;
}

void config_delete(config_key key)
{
	int offset = config_find(key);
	uint8_t null_key[4] = {0, 0, 0xff, 0xff};
	if (offset < 0)
		return;
	flash_write(config_area + offset, null_key, 4);
}

void config_enumerate_start(config_iterator *iterator)
{
	*iterator = CONFIG_AREA_OFFSET;
}

config_key config_enumerate(config_iterator *iterator)
{
	config_key key;

	if (*iterator >= (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE))
		return CONFIG_KEY_INVALID;

	while (CONFIG_KEY(*iterator) == CONFIG_KEY_INVALID) {
		*iterator += CONFIG_TOTLEN(*iterator);
		if (*iterator >= (CONFIG_AREA_SIZE - CONFIG_HEADER_SIZE))
			return CONFIG_KEY_INVALID;
	}

	if (CONFIG_KEY(*iterator) == CONFIG_KEY_UNPROGRAMMED)
		return CONFIG_KEY_INVALID;
	key = CONFIG_KEY(*iterator);
	*iterator += CONFIG_TOTLEN(*iterator);
    return key;
}

uint8_t config_get8(config_key key)
{
	uint8_t data = 0;
	config_get(key, &data, 1);
	return data;
}

uint16_t config_get16(config_key key)
{
	uint16_t data = 0;
	config_get(key, (uint8_t *)&data, 2);
	return data;
}

uint32_t config_get32(config_key key)
{
    uint32_t data = 0;
    config_get(key, (uint8_t *)&data, 4);
    return data;
}

const char *config_key_to_name(config_key key)
{
    int i;
	for (i = 0; i < ARRAY_SIZE(config_key_table); i++) {
		if (config_key_table[i].key == key)
			return config_key_table[i].name;
	}
	return NULL;
}

config_key config_key_from_name(const char *name)
{
    int i;
	for (i = 0; i < ARRAY_SIZE(config_key_table); i++) {
		if (strcmp(config_key_table[i].name, name) == 0)
			return config_key_table[i].key;
	}
	return CONFIG_KEY_INVALID;
}
