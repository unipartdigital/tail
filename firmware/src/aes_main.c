#include <stdio.h>

#include "aes_cmac_test.h"

int main(int argc, char **argv) {
    test_subkey();
    test_cmac_empty();
    test_cmac16();
    test_cmac40();
    test_cmac64();
    return 0;
}
