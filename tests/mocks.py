import tornado.gen
from tornado.httpclient import HTTPRequest, HTTPResponse


class MockApiClient(object):
    def __init__(self, service):
        self.service = service

    @tornado.gen.coroutine
    def get(self, path, **kwargs):
        return self._get_response('GET', path)

    @tornado.gen.coroutine
    def put(self, path, **kwargs):
        return self._get_response('PUT', path)

    @tornado.gen.coroutine
    def patch(self, path, **kwargs):
        return self._get_response('PATCH', path)

    @tornado.gen.coroutine
    def post(self, path, **kwargs):
        return self._get_response('POST', path)

    @tornado.gen.coroutine
    def delete(self, path, **kwargs):
        return self._get_response('DELETE', path)

    def _get_response(self, verb, path):
        response = HTTPResponse(request=HTTPRequest(path, verb), code=200)
        setattr(response, 'json', {})
        return response
