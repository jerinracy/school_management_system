"""Custom pagination classes."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """Standard page number pagination for the API.

    Enforces maximum page size of 100 to prevent unbounded query memory issues.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list) -> Response:
        count = self.page.paginator.count if self.page is not None else len(data)
        return Response(
            {
                "count": count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
