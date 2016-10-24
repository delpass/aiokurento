import aiohttp
import asyncio
import json
import logging
from uuid import uuid4
from asyncio.base_events import BaseEventLoop

logger = logging.getLogger(__name__)


class KurentoTransportException(Exception):
    def __init__(self, message, response=None):
        print(message, response)
        super(KurentoTransportException, self).__init__(message)
        self.response = response
        if response is None:
            self.response = {}
        self.message = message

    def __str__(self):
        return "%s - %s" % (str(self.message), json.dumps(self.response))

# create_future is new in version 3.5.2
if hasattr(BaseEventLoop, 'create_future'):
    def create_future(loop):
        return loop.create_future()
else:
    def create_future(loop):
        return asyncio.Future(loop=loop)


def _set_result(fut, result):
    if fut.done():
        logger.debug("Waiter future is already done %r", fut)
        assert fut.cancelled(), (
            "waiting future is in wrong state", fut, result)
    else:
        fut.set_result(result)


def _set_exception(fut, exception):
    if fut.done():
        logger.debug("Waiter future is already done %r", fut)
        assert fut.cancelled(), (
            "waiting future is in wrong state", fut, exception)
    else:
        fut.set_exception(exception)


class KurentoTransport(object):
    _ws = None
    # _waiters = deque()
    _waiters = {}

    def __init__(self, url, loop=None):
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
        self._reader_task = asyncio.ensure_future(self._reader(),
                                                  loop=self._loop)

    # def __del__(self):
    #     logger.debug("Destroying KurentoTransport with url: %s" % self.url)
    #     self.stopped = True
    #     self._ws.close()

    async def _reader(self):
        logging.debug("KURENTO connected %s" % self.url)
        self._ws = await self.session.ws_connect(self.url)
        while not self.stopped:
            msg = await self._ws.receive()
            if msg.tp == aiohttp.MsgType.text:
                if msg.data == 'close':
                    await self._ws.close()
                    self._ws = await self.session.ws_connect(self.url)
                    # break
                else:
                    await self._on_message(msg.data)
            elif msg.tp == aiohttp.MsgType.closed:
                self._ws = await self.session.ws_connect(self.url)
                # break
            elif msg.tp == aiohttp.MsgType.error:
                self._ws = await self.session.ws_connect(self.url)
                # break
            # except aiohttp.errors.ServerDisconnectedError:
            #     logging.debug("KURENTO drop conection %s" % self.url)
        # return None

    def _next_id(self):
        self.current_id = uuid4().hex
        return str(self.current_id)

    async def _on_message(self, message):
        resp = json.loads(message)
        logger.debug("KURENTO received message: %s" % message)
        msg_id = str(resp.get('id'))
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
                self.session_id = resp['params'].get('sessionId',
                                                     self.session_id)
                asyncio.ensure_future(fn(resp["params"]["value"]))
                # await task
                return None
            if resp['method'] == 'onEvent':
                print("SUB NOT FOUND!!!!11111")
                print(resp)

        elif 'error' in resp:
            waiter = self._waiters.get(msg_id)
            error = resp['error'].get('message', 'Unknown Error')
            _set_exception(waiter, KurentoTransportException(error, resp))
        elif 'result' in resp and 'value' in resp['result']:
            waiter = self._waiters.get(msg_id)
            _set_result(waiter, resp['result']['value'])

        else:
            if 'result' in resp and 'sessionId' in resp['result']:
                self.session_id = resp['result']['sessionId']

    def _rpc(self, rpc_type, **args):
        if self.session_id:
            args["sessionId"] = self.session_id

        request = {
          "jsonrpc": "2.0",
          "id": self._next_id(),
          "method": rpc_type,
          "params": args
        }
        logger.debug("KURENTO sending message:  %s" % json.dumps(request))
        # print(request)
        fut = create_future(loop=self._loop)
        self._ws.send_str(json.dumps(request))
        self._waiters[request['id']] = fut
        return fut

    def create(self, obj_type, **args):
        return self._rpc("create", type=obj_type, constructorParams=args)

    def invoke(self, object_id, operation, **args):
        return self._rpc("invoke", object=object_id, operation=operation,
                         operationParams=args)

    async def subscribe(self, object_id, event_type, fn):
        logging.debug('+-==================================================_=')
        subscription_id = await self._rpc("subscribe", object=object_id,
                                          type=event_type)
        self.subscriptions[str(object_id)] = fn
        return subscription_id

    def unsubscribe(self, subscription_id):
        del self.subscriptions[subscription_id]
        return self._rpc("unsubscribe", subscription=subscription_id)

    def release(self, object_id):
        return self._rpc("release", object=object_id)

    async def stop(self):
        logger.debug("Destroying KurentoTransport with url: %s" % self.url)
        self.stopped = True
        await self._ws.close()
        await self.session.close()
