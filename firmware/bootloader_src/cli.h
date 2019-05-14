/* cli.h */

#ifndef _CLI_H
#define _CLI_H

#include <stdbool.h>

void cli_poll(void);
void cli_init(void);
bool cli_prepare_sleep(void);

#endif
