# import websocket
import aiohttp
import asyncio
import json
import time
import threading
import logging

logger = logging.getLogger(__name__)


class KurentoTransportException(Exception):
    def __init__(self, message, response={}):
        super(KurentoTransportException, self).__init__(message)
        self.response = response

    def __str__(self):
        return "%s - %s" % (str(self.message), json.dumps(self.response))


class KurentoTransport(object):
    ws = None

    def __init__(self, url):
        logging.debug("KURENTO Creating new Transport with url: %s" % url)
        self.url = url
        self.session = aiohttp.ClientSession()
        # self.ws = await websockets.connect(url)
        self.current_id = 0
        self.session_id = None
        self.pending_operations = {}
        self.subscriptions = {}
        self.stopped = False
        # loop = asyncio.get_event_loop()
        # self.task = loop.create_task(self._run_thread())

    async def connect(self):
        self.ws = await self.session.ws_connect(self.url)
        asyncio.ensure_future(self._run_thread())
        logging.debug("KURENTO connected %s" % self.url)

    def __del__(self):
        logger.debug("Destroying KurentoTransport with url: %s" % self.url)
        self.stopped = True
        self.ws.close()

    # def _check_connection(self):
    #     if self.ws.closed:
    #         logger.info("Kurent Client websocket is not connected, reconnecting")
    #         try:
    #             with Timeout(seconds=5):
    #                 self.ws = yield from aiohttp.ws_connect(self.url)
    #                 logger.info("Kurent Client websocket connected!")
    #         except TimeoutException:
    #             # modifying this exception so we can differentiate in the receiver thread
    #             raise KurentoTransportException("Timeout: Kurento Client websocket connection timed out")

    @asyncio.coroutine
    def _run_thread(self):
        if self.ws is None:
            yield from self.connect()
        while not self.stopped:
            msg = yield from self.ws.receive()
            if msg.tp == aiohttp.MsgType.text:
                if msg.data == 'close':
                    yield from self.ws.close()
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

        if 'method' in resp:
            if (resp['method'] == 'onEvent'):
                print("SUBSCRIPTIONS", self.subscriptions)
            if (resp['method'] == 'onEvent' and 'params' in resp and 'value' in resp['params'] and
                    'type' in resp['params']['value'] and resp['params']['value']['object'] in self.subscriptions):
                sub_id = resp['params']['value']['object']
                fn = self.subscriptions[sub_id]
                self.session_id = resp['params']['sessionId'] if 'sessionId' in resp['params'] else self.session_id
                fn(resp["params"]["value"])

        else:
            if 'result' in resp and 'sessionId' in resp['result']:
                self.session_id = resp['result']['sessionId']
            self.pending_operations["%d_response" % resp["id"]] = resp

    @asyncio.coroutine
    def _rpc(self, rpc_type, **args):
        if self.session_id:
            args["sessionId"] = self.session_id

        request = {
          "jsonrpc": "2.0",
          "id": self._next_id(),
          "method": rpc_type,
          "params": args
        }
        req_key = "%d_request" % request["id"]
        resp_key = "%d_response" % request["id"]
        self.pending_operations[req_key] = request
        # if self.ws is None:
        #     yield from self.connect()
        logger.debug("KURENTO sending message:  %s" % json.dumps(request))
        if self.ws is None:
            yield from self.connect()
        self.ws.send_str(json.dumps(request))
        # TODO: Переделать нормально
        while (resp_key not in self.pending_operations):
            yield from asyncio.sleep(0.50)  # wait 50 ms
        resp = self.pending_operations[resp_key]

        del self.pending_operations[req_key]
        del self.pending_operations[resp_key]

        if 'error' in resp:
            raise KurentoTransportException(resp['error']['message'] if 'message' in resp['error'] else 'Unknown Error', resp)
        elif 'result' in resp and 'value' in resp['result']:
            return resp['result']['value']
        else:
            return None  # just to be explicit

    def create(self, obj_type, **args):
        rpc = self._rpc("create", type=obj_type, constructorParams=args)
        return rpc

    def invoke(self, object_id, operation, **args):
        return self._rpc("invoke", object=object_id, operation=operation, operationParams=args)

    async def subscribe(self, object_id, event_type, fn):
        logging.debug('======================================================')
        subscription_id = await self._rpc("subscribe", object=object_id, type=event_type)
        self.subscriptions[object_id] = fn
        return subscription_id

    def unsubscribe(self, subscription_id):
        del self.subscriptions[subscription_id]
        return self._rpc("unsubscribe", subscription=subscription_id)

    def release(self, object_id):
        return self._rpc("release", object=object_id)

    def stop(self):
        self.ws.close()
