/* config.h */

#ifndef _CONFIG_H
#define _CONFIG_H

#include <stdint.h>
#include <stdbool.h>

#define CONFIG_KEYS \
	X(eui,               0x0001) \
	X(xtal_trim,         0x0002) \
	X(role,              0x0003) \
	X(antenna_delay_tx,  0x0004) \
	X(antenna_delay_rx,  0x0005)

#define CONFIG_KEY_INVALID 0x0000

#define CONFIG_KEY_MAXLEN 255

#define X(name, num) config_key_##name = num,
enum config_keys {
		CONFIG_KEYS
};
#undef X

typedef enum config_keys config_key;

/* Call this once before using any config functions */
void config_init(void);

/* Returns length of key, or negative if key not found */
int config_len(config_key key);

/* Gets a key. Returns number of bytes read if successful, or negative on failure. */
int config_get(config_key key, uint8_t *data, int maxlen);

/* Writes a key. Returns true if successful or false if not. */
bool config_put(config_key key, uint8_t *data, int len);

/* Deletes a key. */
void config_delete(config_key key);

/* Reads 8 bits from a key. Returns 0 if unsuccessful. */
uint8_t config_get8(config_key key);

/* Reads 16 bits from a key. Returns 0 if unsuccessful. */
uint16_t config_get16(config_key key);

/* Reads 32 bits from a key. Returns 0 if unsuccessful. */
uint32_t config_get32(config_key key);

typedef int config_iterator;

/* Call config_enumerate_start() to start iterating over
 * all keys, and config_enumerate() to get the next key.
 * Returns CONFIG_KEY_INVALID when there are no more keys.
 * Behaviour is undefined if keys are changed between calls.
 * Restart iteration if keys are modified.
 */
void config_enumerate_start(config_iterator *iterator);
config_key config_enumerate(config_iterator *iterator);


const char *config_key_to_name(config_key key);
config_key config_key_from_name(const char *name);

#endif
