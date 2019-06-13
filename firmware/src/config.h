/* config.h */

#ifndef _CONFIG_H
#define _CONFIG_H

#include <stdint.h>
#include <stdbool.h>

#define CONFIG_KEYS \
	X(eui,               0x0001) \
	X(xtal_trim,         0x0002) \
	X_OBSOLETE(role,              0x0003) \
	X(antenna_delay_tx,  0x0004) \
	X(antenna_delay_rx,  0x0005) \
	X(chan,              0x0006) \
	X(prf_high,          0x0007) \
	X(tx_plen,           0x0008) \
	X(rx_pac,            0x0009) \
	X(tx_pcode,          0x000a) \
	X(rx_pcode,          0x000b) \
	X(ns_sfd,            0x000c) \
	X(data_rate,         0x000d) \
	X(long_frames,       0x000e) \
	X(sfd_timeout,       0x000f) \
	X(associated,        0x0010) \
	X(pan,               0x0011) \
	X(short_addr,        0x0012) \
	X_OBSOLETE(tag_target_addr,   0x0013) \
	X_OBSOLETE(tag_source_port,   0x0014) \
	X_OBSOLETE(tag_dest_port,     0x0015) \
	X(tag_period,        0x0016) \
	X(tx_power,          0x0017) \
	X(smart_tx_power,    0x0018) \
	X(turnaround_delay,  0x0019) \
	X(rxtimeout,         0x001a) \
	X(tag_period_idle,   0x001b) \
	X(tag_transition_time, 0x001c) \
	X(accel_sensitivity, 0x001d) \
	X(accel_exponent,    0x001e) \
	X(accel_mode,        0x001f) \
	X(accel_count,       0x0020) \
	X_OBSOLETE(tag_two_way,       0x0021) \
	X(tag_max_anchors,   0x0022) \
	X(tag_min_responses, 0x0023) \
	X(allow_flat_battery, 0x0024) \
	X(radio_leds,        0x0025) \
	X(xtal_volts,        0x0026) \
	X(xtal_temp,         0x0027) \
	X(uart_drive,        0x0028) \
	X(tx_battery_voltage,0x0029) \
	X(tx_radio_voltage,  0x002a) \
	X(tx_temperature,    0x002b) \
	X(tx_uptime_blinks,  0x002c) \
	X(rxdelay,           0x002d)

#define CONFIG_KEY_INVALID 0x0000

#define CONFIG_KEY_MAXLEN 255

#define X_OBSOLETE(name, num)
#define X(name, num) config_key_##name = num,
enum config_keys {
		CONFIG_KEYS
};
#undef X
#undef X_OBSOLETE

/* We still need the names of the config keys to appear in the cli, but
 * we do want a compile error if we try to use them anywhere in the code.
 */
#define X_OBSOLETE(name, num) X(name, num)



typedef enum config_keys config_key;

/* Call this once before using any config functions */
void config_init(void);

/* Returns length of key, or negative if key not found */
int config_len(config_key key);

/* Gets a key. Returns number of bytes read if successful, or negative on failure. */
int config_get(config_key key, uint8_t *data, int maxlen);

/* Writes a key. Returns true if successful or false if not. */
bool config_put(config_key key, uint8_t *data, int len);

/* Checks if a key and its contents are already in place.
 * Returns true if a key exists and already has identical contents.
 * Returns false otherwise.
 */
bool config_key_in_place(config_key key, uint8_t *data, int len);

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

/* Check if a given iterator is valid. True if valid, false
 * otherwise.
 */
bool config_enumerate_valid(config_iterator *iterator);

const char *config_key_to_name(config_key key);
config_key config_key_from_name(const char *name);

/* Same rules as for config_enumerate */
void config_enumerate_key_names_start(config_key *key);
const char *config_enumerate_key_names(config_key *key);


/* To do an atomic write on a number of keys:
 * int free = config_freespace();
 * int delta = 0;
 * for each key:
 *   delta += config_space_required_for_key(key length);
 *   delta -= config_space_used_by_key(key id);
 * if (free < delta)
 *   report out of space error;
 */

int config_freespace(void);
int config_space_used_by_key(config_key key);
int config_space_required_for_key(int len);

/* Debug only - dump internal data structure */
void config_dump(void);

#endif
