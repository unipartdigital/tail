
SRCS := aes_x86.c aes_cmac.c aes_main.c aes_cmac_test.c x86_util.c util.c

CRYPTO := -I"/home/luke/opt/libressl/include" -L"/home/luke/opt/libressl/lib/"

all: $(SRCS)
	gcc -g $(CRYPTO) -o cmac $(SRCS) -lcrypto -Wall
	gcc -g $(CRYPTO) -o hm hm.c x86_util.c aes_x86.c -lcrypto -Wall

clean:
	rm -f *.o cmac
