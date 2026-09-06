"""Build and optionally submit a product catalog payload."""

import argparse
import enum
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent
PRODUCT_CATALOG_DIR = SCRIPTS_DIR.parent
PROJECT_DIR = PRODUCT_CATALOG_DIR.parent.parent
sys.path.extend([str(PROJECT_DIR), str(PRODUCT_CATALOG_DIR)])

from product_catalog import (
    Attribute,
    Attributes,
    Availability,
    Catalog,
    CatalogSubmissionRequest,
    Categories,
    Category,
    Currency,
    Fulfillment,
    Identifier,
    Inventory,
    Locale,
    Media,
    MediaItems,
    MediaKind,
    Price,
    Product,
    ProductIdentity,
    Products,
    Sku,
    SubmissionMode,
    SubmissionOptions,
    Variant,
    Variants,
)
from dovetail.pylib.client import Client


def build_catalog_submission() -> CatalogSubmissionRequest:
    """Create a representative catalog submission matching product_catalog.xsd."""
    category = Category(id=Identifier("shirts"), name="Shirts")
    variant = Variant(
        sku=Sku("TSHIRT-BLUE-M"),
        price=Price(amount=24.99, currency=Currency("USD")),
        inventory=Inventory(quantity=25, availability=Availability.in_stock),
    )
    product = Product(
        identity=ProductIdentity(
            sku=Sku("TSHIRT-BLUE"),
            name="Blue T-Shirt",
            description="Classic cotton t-shirt.",
            brand="Dovetail",
        ),
        variants=Variants(variant=[variant]),
        media=MediaItems(
            media=[
                Media(
                    url="https://example.com/products/tshirt-blue.jpg",
                    kind=MediaKind.image,
                    altText="Blue t-shirt",
                )
            ]
        ),
        attributes=Attributes(attribute=[Attribute(name="material", value="cotton")]),
        fulfillment=Fulfillment(weightGrams=180, requiresShipping=True, returnable=True),
    )
    return CatalogSubmissionRequest(
        catalog=Catalog(
            name="Dovetail Store",
            locale=Locale("en-US"),
            currency=Currency("USD"),
            categories=Categories(category=[category]),
        ),
        products=Products(product=[product]),
        submissionOptions=SubmissionOptions(mode=SubmissionMode.upsert, dryRun=True),
    )


def to_payload(submission: CatalogSubmissionRequest) -> dict:
    """Convert generated dataclasses and enums to the catalog submission payload."""
    def convert(value):
        if isinstance(value, enum.Enum):
            return value.value
        if is_dataclass(value):
            return convert(asdict(value))
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return {"catalogSubmissionRequest": convert(submission)}


def parse_args() -> argparse.Namespace:
    """Parse the optional send flag."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="submit to the configured service")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    payload = to_payload(build_catalog_submission())
    print(json.dumps(payload, indent=2))

    if args.send:
        config_file = PRODUCT_CATALOG_DIR / "config.cfg"
        response = Client(config_file=str(config_file)).send_request(payload)
        print(json.dumps(response, indent=2))