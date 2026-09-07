# Dovetail

Dovetail generates Python components from XML Schema Definition (XSD) models. It is intended for building structured requests and responses whose shape is known from a schema, while keeping construction incremental and inspectable.

The repository currently demonstrates the approach with the product catalog example in [examples/product_catalog](examples/product_catalog). That directory contains the schema, generated dataclasses, generated request/response components, callback extension points, a fake client, and a runnable submission script. See its [README.md](examples/product_catalog/README.md) for the complete example and command-line workflow.

## The Architecture

The pipeline has three main layers:

```text
XSD schema
    |
    v
xsd_to_py_class.py
    |
    v
Python dataclasses
    |
    v
py_code_gen.py
    |
    v
callable component modules
```

`xsd_to_py_class.py` translates schema types, fields, restrictions, enums, and common occurrence rules into Python dataclasses and named primitive types. `py_code_gen.py` reads those dataclasses and generates component modules for the configured request and response roots.

The runtime support is in [dovetail/pylib](dovetail/pylib):

- `decorators.py` supplies `component`, `Component`, and typed list behavior.
- `wire.py` reconstructs generated components from wire-format dictionaries.
- `client.py` composes a configured API layer and service/transport layer.

## Why Dataclasses Matter

Generated model classes are dataclasses, not ordinary classes with manually managed properties. This is important because the runtime and generators rely on dataclass metadata and behavior:

- `dataclasses.fields()` provides the schema field names and declarations.
- The generated constructor gives every component a predictable initialization contract.
- Type annotations allow `get_type_hints()` to resolve nested models, lists, unions, enums, and restricted scalar types.
- `dataclasses.asdict()` and related tooling provide a standard model representation, although Dovetail's runtime serializer deliberately reads assigned fields directly to avoid allocating omitted lazy fields.
- `is_dataclass()` lets the client and wire utility distinguish structured model values from primitive values.

A regular class with properties could imitate some of this behavior, but it would not automatically provide the field metadata, constructor contract, type-hint surface, and standard dataclass interoperability on which the generator depends.

## What `@component` Does

Generated component modules contain code like this:

```python
@component(Catalog)
def catalog(
    catalog: Catalog,
    name: str,
    locale: Locale,
    currency: Currency,
):
    ...
```

This looks like a normal decorated function, but Python applies decorators in two stages. The code is effectively interpreted as:

```python
catalog = component(Catalog)(catalog)
```

The first call, `component(Catalog)`, invokes `component.__new__`. It records the dataclass fields and dynamically creates a class with multiple inheritance:

```python
GeneratedCatalog = type("Catalog", (Component, Catalog), {})
```

The returned class inherits both:

- `Catalog`, preserving the generated dataclass fields and constructor.
- `Component`, adding callable behavior, lazy nested-property allocation, operation results, and serialization.

Python then calls the returned class with the original function object:

```python
catalog = GeneratedCatalog(catalog)
```

That invokes `Component.__init__`, which stores the original function as the component's behavior hook. The module-level name `catalog` no longer refers to a function; it refers to a callable instance of `GeneratedCatalog`.

This is why importing a generated name that appears to be a function actually imports an object:

```python
from catalog_submission_request import catalog
```

`catalog` is callable because `Component.__call__` is available on the generated wrapper instance. It is also a dataclass-derived component object with access to its schema fields and runtime state.

## Calling A Component

A component can be used first as a factory and then as a populated model:

```python
from catalog_submission_request import catalog

catalog_instance = catalog(
    name="Dovetail Store",
    locale="en-US",
    currency="USD",
)
```

`Component.__call__` creates or reuses the component instance, maps submitted snake_case arguments to schema field names, assigns the values, invokes the behavior hook, stores its return value as `operation_result`, and returns the populated component instance.

The returned object can therefore be inspected directly:

```python
catalog_instance.name
catalog_instance.locale
catalog_instance.operation_result
```

The behavior hook may return `None`, a boolean, a dictionary, a list, or another application-defined value. A developer-owned callback may use that hook for validation, normalization, enrichment, diagnostics, or derived values.

## Lazy Properties And Daisy Chaining

Complex fields are allocated when they are accessed. A chain such as:

```python
request.products.product
```

walks through the generated model by resolving each schema property. The runtime creates the missing component wrapper, assigns it to the parent, and returns it. This makes longer assembly chains possible:

```python
request.catalog.categories.category(shirts)
product.variants.variant(medium_blue_tshirt)
```

Primitive values are assigned by calling the component representing the current complex element:

```python
product.identity(
    sku="TSHIRT-BLUE",
    name="Blue T-Shirt",
)
```

The caller can also construct a complex element independently and attach it later. This avoids one large, deeply indented constructor and allows each element to be validated or enriched before it enters the larger tree.

## Typed Lists

Repeated XSD elements become typed lists. They enforce the declared element type and support ordinary list operations:

```python
product.variants.variant[0]
product.variants.variant.pop(1)
```

A named attribute can create and retain an alias for a new list element:

```python
mistake = product.variants.variant.large_blue_tshirt
mistake(sku="TSHIRT-BLUE-L")
removed = product.variants.variant.remove("large_blue_tshirt")
```

Calling a list adds an independently assembled item and returns the added item. `remove(name)` returns all elements associated with that name and updates the remaining alias indexes.

## Callbacks

Generated component modules import a root-specific callback module, for example:

```python
import catalog_submission_request_callbacks as callbacks
```

The generated component checks for a matching hook and returns `None` when that hook is not implemented. Hook execution itself is not swallowed, so a developer can deliberately raise an exception for a failed validation or enrichment step.

The generator writes the current hook signatures to `_generated_callbacks.py`. It creates the developer-owned `*_callbacks.py` files only when they do not exist, so regeneration does not erase custom code.

## Clients And Wire Conversion

The generic client in `dovetail.pylib.client` reads a configuration file beside the caller, or an explicitly supplied config path. It loads the configured API and service module/class pairs and composes them into one client object.

The product catalog defaults to a fake loopback client. It serializes the request to JSON wire data, creates a response wire document, and reconstructs that document as a decorated response component through `dovetail.pylib.wire.wire_to_component`.

The response can then be interrogated as a generated component:

```python
response.status
response.acceptedProducts
response.rejectedProducts
response.operation_result
```

The client and service choices are configuration-driven, so a real transport can replace the fake loopback without changing request assembly code.

## Build And Explore

From the product catalog directory:

```bash
cd examples/product_catalog
make clean
make
python scripts/submit_product_catalog.py
python scripts/submit_product_catalog.py --send
```

The default `--send` command uses the fake client and does not require a running service. The generated request/response component modules are promoted into the example directory after generation; temporary build output is removed.

For the full schema, component assembly, list correction, callback, client, and response examples, read [examples/product_catalog/README.md](examples/product_catalog/README.md).
