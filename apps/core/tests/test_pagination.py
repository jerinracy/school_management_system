"""Unit tests for pagination."""

from typing import Any, cast

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.pagination import StandardResultsSetPagination


class TestStandardPagination:
    def test_pagination_defaults(self) -> None:
        pagination = StandardResultsSetPagination()
        assert pagination.page_size == 20
        assert pagination.max_page_size == 100
        assert pagination.page_size_query_param == "page_size"

    def test_paginated_response_structure(self) -> None:
        factory = APIRequestFactory()
        request = factory.get("/api/v1/test/?page=1&page_size=20")
        drf_request = Request(request)

        pagination = StandardResultsSetPagination()
        dataset: Any = list(range(1, 50))  # 49 items
        page: list[Any] | None = pagination.paginate_queryset(cast(Any, dataset), drf_request)

        assert page is not None
        assert len(page) == 20

        response = pagination.get_paginated_response(page)
        data = response.data
        assert "count" in data
        assert "next" in data
        assert "previous" in data
        assert "results" in data
        assert data["count"] == 49
        assert len(data["results"]) == 20
