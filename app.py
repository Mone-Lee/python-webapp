import logging; logging.basicConfig(level=logging.INFO)

from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


app = web.Application()
app.router.add_route('GET', '/', index)
logging.info('Server is running at http://0.0.0.0:8080/ ...')

web.run_app(app)
