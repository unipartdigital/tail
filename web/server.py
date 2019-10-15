#!/usr/bin/python3

"""Tail demo server"""

from aiohttp import web
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)

routes = web.RouteTableDef()
dist = Path(__file__).resolve().parent / 'dist'

@routes.get('/')
@routes.get('/map')
@routes.get('/list')
async def index(request):
    return web.FileResponse(dist / 'index.html')

app = web.Application()
app.router.add_static('/dist', dist)
app.router.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app)
