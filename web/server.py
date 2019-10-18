#!/usr/bin/python3

"""Tail demo server"""

import argparse
from aiohttp import web
import asyncio
import json
from pathlib import Path
import logging

RS = b'\x1f'
RADIUS = 0.2

logging.basicConfig(level=logging.INFO)
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
    (reader, writer) = await asyncio.open_connection(app['host'], app['port'])
    while True:
        raw = await reader.readuntil(RS)
        data = json.loads(raw.rstrip(RS))
        logger.debug("Received: %s", data)
        if data['Type'] != 'TAG':
            continue
        notice = {
            data['Tag']: {
                'name': data['Name'],
                'color': data['Colour'],
                'x': data['Coord'][0],
                'y': data['Coord'][1],
                'z': data['Coord'][2],
                'r': RADIUS,
            },
        }
        logger.debug("Notifying %d clients: %s", len(app['clients']), notice)
        for queue in app['clients']:
            queue.put_nowait(notice)

async def start_notifier(app):
    app['notifier'] = asyncio.create_task(notifier(app))

async def cleanup_notifier(app):
    app['notifier'].cancel()
    await app['notifier']

def run(host, port):
    app = web.Application()
    app['clients'] = set()
    app['host'] = host
    app['port'] = port
    app.on_startup.append(start_notifier)
    app.on_cleanup.append(cleanup_notifier)
    app.router.add_static('/dist', dist)
    app.router.add_routes(routes)
    web.run_app(app)

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', type=int, default=9475)
parser.add_argument('host', type=str)

if __name__ == '__main__':
    args = parser.parse_args()
    run(args.host, args.port)
