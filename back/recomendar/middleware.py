import time, logging
from typing import Callable
logger = logging.getLogger("recomendar.request")

class RequestTimingMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        response = self.get_response(request)
        logger.info("%s %s -> %s in %.3fs",
                    request.method, request.path, getattr(response, "status_code", "?"),
                    time.time() - t0)
        return response
