from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
from product_catalog import CatalogSubmissionResponse, SubmissionStatus
from pylib.decorators import typedlist, component

#--------------------------------------------------------------------------------------------------------------
#                                           CatalogSubmissionResponse:CatalogSubmissionResponse                                           
#--------------------------------------------------------------------------------------------------------------
@component(CatalogSubmissionResponse)
def catalog_submission_response(
    catalog_submission_response:CatalogSubmissionResponse,
    submission_id:str,
    status:str | SubmissionStatus,
    accepted_products:int,
    rejected_products:int,
    message:str | None=None,
):
    """
    the element is populated as:
    catalog_submission_response(
        submission_id = submission_id_value # mandatory
        status = status_value # mandatory
        accepted_products = accepted_products_value # mandatory
        rejected_products = rejected_products_value # mandatory
        message = message_value # optional
    )
    the element population operation returns a reference to the catalog_submission_response element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: submission_id=%s,status=%s,accepted_products=%s,rejected_products=%s,message=%s',
    submission_id, status, accepted_products, rejected_products, message)

    logger.debug('committed message properties: submission_id=%s, status=%s, accepted_products=%s, rejected_products=%s, message=%s',
    catalog_submission_response.submission_id, catalog_submission_response.status, catalog_submission_response.accepted_products, catalog_submission_response.rejected_products, catalog_submission_response.message)
