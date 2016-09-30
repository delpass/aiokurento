# import websocket
import aiohttp
import asyncio
import json
import time
import threading
import logging
from collections import deque
from asyncio.base_events import BaseEventLoop

logger = logging.getLogger(__name__)


class KurentoTransportException(Exception):
    def __init__(self, message, response={}):
        super(KurentoTransportException, self).__init__(message)
        self.response = response

    def __str__(self):
        return "%s - %s" % (str(self.message), json.dumps(self.response))

# create_future is new in version 3.5.2
if hasattr(BaseEventLoop, 'create_future'):
    def create_future(loop):
        return loop.create_future()
else:
    def create_future(loop):
        return asyncio.Future(loop=loop)


class KurentoTransport(object):
    _ws = None
    _waiters = deque()

    def __init__(self, url, loop = None):
        logging.debug("KURENTO Creating new Transport with url: %s" % url)
        self.url = url
        self.session = aiohttp.ClientSession()
        self.current_id = 0
        self.session_id = None
        self.subscriptions = {}
        self.stopped = False
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._reader_task = asyncio.ensure_future(self._reader())

    def __del__(self):
        logger.debug("Destroying KurentoTransport with url: %s" % self.url)
        self.stopped = True
        self._ws.close()

    async def _reader(self):
        logging.debug("KURENTO connected %s" % self.url)
        await self.session.ws_connect(self.url)
        while not self.stopped:
            msg = await self._ws.receive()
            if msg.tp == aiohttp.MsgType.text:
                if msg.data == 'close':
                    await self._ws.close()
                    break
                else:
                    self._on_message(msg.data)
            elif msg.tp == aiohttp.MsgType.closed:
                break
            elif msg.tp == aiohttp.MsgType.error:
                break

    def _next_id(self):
        self.current_id += 1
        return self.current_id

    def _on_message(self, message):
        resp = json.loads(message)
        logger.debug("KURENTO received message: %s" % message)

        if 'error' in resp:
            error = resp['error'].get('message', 'Unknown Error')
            raise KurentoTransportException(error, resp)
        elif 'result' in resp and 'value' in resp['result']:
            return resp['result']['value']

        if 'method' in resp:
            if resp['method'] == 'onEvent':
                print("SUBSCRIPTIONS", self.subscriptions)
            if (resp['method'] == 'onEvent' and
                    'params' in resp and
                    'value' in resp['params'] and
                    'type' in resp['params']['value'] and
                    resp['params']['value']['object'] in self.subscriptions):
                sub_id = str(resp['params']['value']['object'])
                logging.warning("sub_id %s" % sub_id)
                fn = self.subscriptions[sub_id]
                self.session_id = resp['params']['sessionId'] if 'sessionId' in resp['params'] else self.session_id
                fn(resp["params"]["value"])

        else:
            if 'result' in resp and 'sessionId' in resp['result']:
                self.session_id = resp['result']['sessionId']

    async def _rpc(self, rpc_type, **args):
        if self.session_id:
            args["sessionId"] = self.session_id

        request = {
          "jsonrpc": "2.0",
          "id": self._next_id(),
          "method": rpc_type,
          "params": args
        }
        logger.debug("KURENTO sending message:  %s" % json.dumps(request))
        fut = create_future(loop=self._loop)
        self._ws.send_str(json.dumps(request))
        self._waiters.append((fut,))
        return fut

    async def create(self, obj_type, **args):
        rpc = await self._rpc("create", type=obj_type, constructorParams=args)
        return rpc

    async def invoke(self, object_id, operation, **args):
        return await self._rpc("invoke", object=object_id, operation=operation,
                               operationParams=args)

    async def subscribe(self, object_id, event_type, fn):
        logging.debug('======================================================')
        subscription_id = await self._rpc("subscribe", object=object_id,
                                          type=event_type)
        self.subscriptions[str(object_id)] = fn
        return subscription_id

    async def unsubscribe(self, subscription_id):
        del self.subscriptions[subscription_id]
        return await self._rpc("unsubscribe", subscription=subscription_id)

    async def release(self, object_id):
        return await self._rpc("release", object=object_id)

    async def stop(self):
        self._ws.close()
