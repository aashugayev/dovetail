# Product Catalog Example

This example shows how Dovetail turns an XSD model into Python components that can be assembled incrementally.

The schema describes a catalog submission containing catalog metadata, categories, products, variants, prices, inventory, media, attributes, fulfillment details, and submission options. The generated Python model is in `product_catalog.py`. The generated request and response component modules are `catalog_submission_request.py` and `catalog_submission_response.py`.

## Why It Is Useful

A conventional approach creates the entire request as one deeply nested dataclass or dictionary expression. That becomes awkward as the schema grows: every level of the tree must be known and maintained in one place.

Dovetail lets a caller:

- Create a root component first.
- Populate primitive properties when they are available.
- Create complex elements independently.
- Attach elements to their parent later.
- Add and remove list elements by index or name.
- Run optional developer-owned evaluation or enrichment hooks as components are populated.
- Serialize only the fields that were explicitly assembled.

This supports interactive construction, validation, enrichment, and correction before a request is submitted.

## Small Example

```python
from catalog_submission_request import (
    catalog_submission_request,
    product_component,
    variant_component,
)

request = catalog_submission_request()
request.catalog(name="Dovetail Store", locale="en-US", currency="USD")

product = product_component()
product.identity(sku="TSHIRT-BLUE", name="Blue T-Shirt")

variant = variant_component(sku="TSHIRT-BLUE-M")
variant.price(amount=24.99, currency="USD")
variant.inventory(quantity=25, availability="in_stock")
product.variants.variant(variant)

request.products.product(product)
request.submission_options(mode="upsert", dry_run=True)

payload = request.to_dict()
```

The result is a request-shaped dictionary rooted at `catalogSubmissionRequest`. The full executable example is in `scripts/submit_product_catalog.py`.

A list item can be corrected after it has been added:

```python
mistake = product.variants.variant.large_blue_tshirt
mistake(sku="TSHIRT-BLUE-L")
removed = product.variants.variant.remove("large_blue_tshirt")
```

Numeric list operations remain available as well:

```python
removed_variant = product.variants.variant.pop(1)
```

The typed-list `remove()` operation returns all elements associated with the requested name. The component addition operation returns the element that was added.

## How It Works

1. `xsd_to_py_class.py` reads `product_catalog.xsd` and generates the typed dataclasses in `product_catalog.py`.
2. `py_code_gen.py` reads the generated dataclasses and creates component factories for the configured request and response roots.
3. The `component` decorator combines each dataclass with the `Component` runtime behavior from `dovetail.pylib`.
4. Accessing a complex property lazily creates its component wrapper. Calling it assigns primitive values to that component.
5. Typed list properties enforce their element type and support normal list access together with named aliases.
6. Generated components import root-specific callback modules. Those modules are developer-owned and are created once, never overwritten by regeneration.
7. Each component can return an evaluation result, which is retained on the instance as `evaluation_result`.

The generated callback contracts are written to `_generated_callbacks.py`. Custom behavior belongs in `catalog_submission_request_callbacks.py` or `catalog_submission_response_callbacks.py`.

## Client Implementation

The example uses `dovetail.pylib.client.Client` as a configurable client
factory. It reads `config.cfg` from the product catalog directory, selects an
API implementation and a service implementation, and combines them into one
client object.

The default configuration uses the local fake loopback service:

```ini
[default]
api=catalog_submission_api
client=fake_loopback

[api]
module=catalog_submission_client
class=ApiClient

[fake_loopback]
module=catalog_submission_client
class=Client
```

The fake client accepts the assembled request, converts it to JSON wire data,
creates a submission response, converts that response back through the wire
format, and returns a decorated `CatalogSubmissionResponse` instance. This
makes the example runnable without a server while still exercising the same
request/response conversion path.

The `[restapi]` section provides an alternative real transport configuration:

```ini
[restapi]
service=http://127.0.0.1:5000
version=v1
application=product-catalog
module=restapi_client
class=Client
```

To use that transport, change the default client selector to
`client=restapi`. The module and class names are read from configuration; the
generic client does not dispatch on hard-coded transport names.

## Build

Run from this directory:

```bash
make clean
make
```

The local `make.cfg` selects the schema, request class, response class, and shared generator paths. Generated request and response modules are promoted into this directory, and the temporary `_dovetail` directory is removed after generation.

## Preview or Submit

Preview the assembled payload without making a network request:

```bash
python scripts/submit_product_catalog.py
```

Use `--send` to submit through the configured client and service:

```bash
python scripts/submit_product_catalog.py --send
```

With the default configuration, `--send` uses the fake loopback and prints the
reconstructed response properties individually:

```text
submission_id=fake-submission-001
status=accepted
accepted_products=1
rejected_products=0
message=Accepted by fake loopback service
evaluation_result=None
```
