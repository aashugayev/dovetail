"""Build and optionally submit a product catalog payload.

The same request could be assembled conventionally as one deeply nested
dictionary, for example::

    payload = {
        "catalogSubmissionRequest": {
            "catalog": {
                "name": "Dovetail Store",
                "locale": "en-US",
                "currency": "USD",
                "categories": {
                    "category": [{"id": "shirts", "name": "Shirts"}],
                },
            },
            "products": {
                "product": [{
                    "identity": {
                        "sku": "TSHIRT-BLUE",
                        "name": "Blue T-Shirt",
                    },
                    "variants": {
                        "variant": [{
                            "sku": "TSHIRT-BLUE-M",
                            "price": {"amount": 24.99, "currency": "USD"},
                            "inventory": {
                                "quantity": 25,
                                "availability": "in_stock",
                            },
                        }],
                    },
                }],
            },
            "submissionOptions": {"mode": "upsert", "dryRun": True},
        },
    }

The component-based example below produces the same shape incrementally. It
lets each complex element and primitive property be created, evaluated, and
attached independently, so the assembly can be inspected or extended at each
step instead of maintaining one large nested dictionary expression.
"""

import argparse
import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent
PRODUCT_CATALOG_DIR = SCRIPTS_DIR.parent
PROJECT_DIR = PRODUCT_CATALOG_DIR.parent.parent
sys.path.extend([str(PROJECT_DIR), str(PRODUCT_CATALOG_DIR)])

from catalog_submission_request import (
    catalog_submission_request,
    category_component,
    product_component,
    variant_component,
)
from dovetail.pylib.client import Client


def build_catalog_submission():
    """Build a catalog request through separately assembled components."""
    # Start with the request root. A single nested dataclass constructor would
    # need to reproduce the complete schema tree in one expression; components
    # instead allocate nested elements when their generated properties are used.
    request = catalog_submission_request()

    # Populate scalar catalog fields through its component factory. The returned
    # Catalog instance is assigned to request.catalog by Component.__getattribute__.
    request.catalog(
        name="Dovetail Store",
        locale="en-US",
        currency="USD",
    )
    # Construct a category independently, then append it through the catalog's
    # typed category list instead of nesting Category inside a full request tree.
    shirts = category_component(id="shirts", name="Shirts")
    request.catalog.categories.category(shirts)

    # Build the product and its nested identity and fulfillment components in
    # separate steps. Each chained property creates only the complex element
    # needed at that point in the schema tree.
    blue_tshirt = product_component()
    blue_tshirt.identity(
        sku="TSHIRT-BLUE",
        name="Blue T-Shirt",
        description="Classic cotton t-shirt.",
        brand="Dovetail",
    )
    blue_tshirt.fulfillment(requires_shipping=True, returnable=True, weight_grams=180)

    # Populate a variant independently, then append it to the product's typed
    # list. The same pattern naturally supports any number of variants.
    medium_blue_tshirt = variant_component(sku="TSHIRT-BLUE-M")
    medium_blue_tshirt.price(amount=24.99, currency="USD")
    medium_blue_tshirt.inventory(quantity=25, availability="in_stock")
    blue_tshirt.variants.variant(medium_blue_tshirt)

    # A second variant can be assembled through a name on the typed list. The
    # name is an alias for the list element, so it can be retrieved or removed
    # later without knowing its numeric position.
    large_blue_tshirt = blue_tshirt.variants.variant.large_blue_tshirt
    large_blue_tshirt(sku="TSHIRT-BLUE-L")
    large_blue_tshirt.price(amount=24.99, currency="USD")
    large_blue_tshirt.inventory(quantity=18, availability="in_stock")
    assert blue_tshirt.variants.variant.large_blue_tshirt.sku == "TSHIRT-BLUE-L"

    # Treat the named second variant as a data-entry mistake. remove() returns
    # all elements carrying that name; numeric indexing remains available too.
    removed_variants = blue_tshirt.variants.variant.remove("large_blue_tshirt")
    assert [variant.sku for variant in removed_variants] == ["TSHIRT-BLUE-L"]

    # Attach the completed product after its required children are assembled.
    request.products.product(blue_tshirt)
    request.submission_options(mode="upsert", dry_run=True)
    return request


def parse_args() -> argparse.Namespace:
    """Parse the optional send flag."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="submit to the configured service")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    request = build_catalog_submission()
    # Serialize only fields assigned during component assembly. Omitted optional
    # schema branches do not appear in the submitted payload.
    payload = request.to_dict()
    print(json.dumps(payload, indent=2))

    if args.send:
        config_file = PRODUCT_CATALOG_DIR / "config.cfg"
        response = Client(config_file=str(config_file)).send_request(request)
        print(f"submission_id={response.submission_id}")
        print(f"status={response.status}")
        print(f"accepted_products={response.accepted_products}")
        print(f"rejected_products={response.rejected_products}")
        print(f"message={response.message}")
        print(f"evaluation_result={response.evaluation_result}")