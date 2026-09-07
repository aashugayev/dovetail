"""Build and optionally submit a product catalog payload."""

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
    request = catalog_submission_request()

    request.catalog(
        name="Dovetail Store",
        locale="en-US",
        currency="USD",
    )
    shirts = category_component(id="shirts", name="Shirts")
    request.catalog.categories.category(shirts)

    blue_tshirt = product_component()
    blue_tshirt.identity(
        sku="TSHIRT-BLUE",
        name="Blue T-Shirt",
        description="Classic cotton t-shirt.",
        brand="Dovetail",
    )
    blue_tshirt.fulfillment(requires_shipping=True, returnable=True, weight_grams=180)

    medium_blue_tshirt = variant_component(sku="TSHIRT-BLUE-M")
    medium_blue_tshirt.price(amount=24.99, currency="USD")
    medium_blue_tshirt.inventory(quantity=25, availability="in_stock")
    blue_tshirt.variants.variant(medium_blue_tshirt)

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
    payload = request.to_dict()
    print(json.dumps(payload, indent=2))

    if args.send:
        config_file = PRODUCT_CATALOG_DIR / "config.cfg"
        response = Client(config_file=str(config_file)).send_request(payload)
        print(json.dumps(response, indent=2))