MAKEFLAGS = "-j 2"
HOST = resistor.qs.unipart.io

all : npm-build

dev : npm-dev server-dev

npm-dev :
	npm run dev

npm-build :
	npm run build

server-dev :
	./server.py ${HOST}
