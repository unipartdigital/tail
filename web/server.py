#!/usr/bin/python3

"""Tail demo server"""

from aiohttp import web
import asyncio
from pathlib import Path
import logging
from random import randrange

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

dist = Path(__file__).resolve().parent / 'dist'
routes = web.RouteTableDef()

@routes.get('/')
@routes.get('/map')
@routes.get('/list')
async def index(request):
    return web.FileResponse(dist / 'index.html')

@routes.get('/tags')
async def tags(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    queue = asyncio.Queue()
    request.app['clients'].add(queue)
    try:
        while True:
            msg = await queue.get()
            await ws.send_json(msg)
    finally:
        request.app['clients'].remove(queue)

async def notifier(app):
    while True:
        await asyncio.sleep(2)
        logger.debug("Notifying %d clients", len(app['clients']))
        tags = {
            "70b3d5b1e0000139": {
                "name": "YORK-871612",
                "x": 500 + randrange(-50, 50),
                "y": 400 + randrange(-50, 50),
                "r": 15,
                "color": "orange",
            },
            "70b3d5b1e0000145": {
                "name": "YORK-456198",
                "x": 200 + randrange(-50, 50),
                "y": 300 + randrange(-50, 50),
                "r": 15,
                "color": "blue",
            },
        };
        for queue in app['clients']:
            queue.put_nowait(tags)

async def start_notifier(app):
    app['notifier'] = asyncio.create_task(notifier(app))

async def cleanup_notifier(app):
    app['notifier'].cancel()
    await app['notifier']

def run():
    app = web.Application()
    app['clients'] = set()
    app.on_startup.append(start_notifier)
    app.on_cleanup.append(cleanup_notifier)
    app.router.add_static('/dist', dist)
    app.router.add_routes(routes)
    web.run_app(app)

if __name__ == '__main__':
    run()
