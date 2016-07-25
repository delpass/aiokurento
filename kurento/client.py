from . import media
from .transport import KurentoTransport


class KurentoClient(object):
    def __init__(self, url):
        """
        :param url: KWS websocket url
        """
        self.url = url
        self.transport = KurentoTransport(self.url)

    def get_transport(self):
        """
        :return: <KurentoTransport> transport
        """
        return self.transport

    async def create_pipeline(self):
        """
        Create media pipeline
        :return: <MediaPipeline>
        """
        return await media.MediaPipeline(self).create()

    async def get_pipeline(self, id):
        """
        Get media pipeline by id
        :param id: <integer> pipeline id
        :return: <MediaPipeline>
        """
        return media.MediaPipeline(self, id=id)
