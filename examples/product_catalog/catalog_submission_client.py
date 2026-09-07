"""Fake loopback service for product catalog submission examples."""

import enum
import json
from dataclasses import asdict, is_dataclass

from product_catalog import CatalogSubmissionResponse, SubmissionStatus
from dovetail.pylib.wire import wire_to_component


class ApiClient:
    """Marker API layer used by the generic client composition."""


class Client:
    """Echo a catalog submission through a JSON wire-format loopback."""

    def send_request(self, request):
        """Serialize a request, loop it through wire JSON, and return a response model."""
        if is_dataclass(request):
            request = asdict(request)
        wire_request = json.dumps(request, default=self._wire_value)
        request_data = json.loads(wire_request)
        product_count = len(request_data.get("products", {}).get("product", []))
        response_data = {
            "submissionId": "fake-submission-001",
            "status": SubmissionStatus.accepted.value,
            "acceptedProducts": product_count,
            "rejectedProducts": 0,
            "message": "Accepted by fake loopback service",
        }
        wire_response = json.dumps(response_data)
        return wire_to_component(
            json.loads(wire_response),
            module_name="catalog_submission_response",
            factory_name="catalog_submission_response",
        )

    @staticmethod
    def _wire_value(value):
        """Convert enum values to their wire representation."""
        return value.value if isinstance(value, enum.Enum) else str(value)