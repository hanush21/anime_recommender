# recomendar/middleware.py
import time
import logging
from typing import Callable

logger = logging.getLogger("recomendar.request")

class RequestTimingMiddleware:
    """
    Loggea: METHOD PATH -> STATUS in X.XXXs
    """
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        response = self.get_response(request)
        dt = time.time() - t0
        logger.info("%s %s -> %s in %.3fs", request.method, request.path, getattr(response, "status_code", "?"), dt)
        return response
