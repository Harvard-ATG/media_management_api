import logging

from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class QueryCountDebugMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if response.status_code == 200:
            total_time = 0
            for query in connection.queries:
                query_time = query.get("time")
                if query_time is None:
                    # django-debug-toolbar monkeypatches the connection
                    # cursor wrapper and adds extra information in each
                    # item in connection.queries. The query time is stored
                    # under the key "duration" rather than "time" and is
                    # in milliseconds, not seconds.
                    query_time = query.get("duration", 0) / 1000
                total_time += float(query_time)
            logger.debug(
                "%s queries run, total %s seconds"
                % (len(connection.queries), total_time)
            )
        return response


class ExceptionLoggingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        logger.exception(
            "Exception logged for request: %s message: %s"
            % (request.path, str(exception))
        )
