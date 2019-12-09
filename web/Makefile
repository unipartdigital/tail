MAKEFLAGS = "-j 2"
HOST = resistor.qs.unipart.io

DESTDIR = /opt/tail/web

all : npm-build

dev : npm-dev server-dev

npm-dev :
	npm run dev

npm-build :
	npm run build

server-dev :
	./server.py ${HOST}

clean :
	$(RM) dist/*

install : npm-build
	mkdir -p $(DESTDIR)/dist
	install -m 755 server.py $(DESTDIR)/
	install -m 644 dist/* $(DESTDIR)/dist/
	install -m 644 nginx-tail.conf /etc/nginx/default.d/tail.conf
