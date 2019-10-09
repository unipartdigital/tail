MAKEFLAGS = "-j 2"

all : npm-build

dev : npm-dev wsgi-dev

npm-dev :
	npm run dev

npm-build :
	npm run build

wsgi-dev :
	FLASK_APP=server/wsgi.py FLASK_DEBUG=1 flask run
