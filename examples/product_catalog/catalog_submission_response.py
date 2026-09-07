from __future__ import annotations

from product_catalog import CatalogSubmissionResponse, SubmissionStatus
from dovetail.pylib.decorators import typedlist, component
import catalog_submission_response_callbacks as callbacks

@component(CatalogSubmissionResponse)
def catalog_submission_response(catalog_submission_response: CatalogSubmissionResponse,
    submission_id: str,
    status: str | SubmissionStatus,
    accepted_products: int,
    rejected_products: int,
    message: str | None = None,
):
    try:
        hook = callbacks.catalog_submission_response
    except AttributeError:
        return None
    return hook(catalog_submission_response, submission_id=submission_id, status=status, accepted_products=accepted_products, rejected_products=rejected_products, message=message)

