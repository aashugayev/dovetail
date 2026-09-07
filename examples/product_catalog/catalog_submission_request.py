from __future__ import annotations

from product_catalog import Attribute, Attributes, Availability, Catalog, CatalogSubmissionRequest, Categories, Category, CategoryRefs, Currency, Fulfillment, Identifier, Inventory, Locale, Media, MediaItems, MediaKind, Price, Product, ProductIdentity, Products, Sku, SubmissionMode, SubmissionOptions, Variant, Variants
from dovetail.pylib.decorators import typedlist, component
import catalog_submission_request_callbacks as callbacks

@component(CatalogSubmissionRequest)
def catalog_submission_request(catalog_submission_request: CatalogSubmissionRequest,
):
    try:
        hook = callbacks.catalog_submission_request
    except AttributeError:
        return None
    return hook(catalog_submission_request)

@component(Catalog)
def catalog(catalog: Catalog,
    name: str,
    locale: Locale,
    currency: Currency,
):
    try:
        hook = callbacks.catalog
    except AttributeError:
        return None
    return hook(catalog, name=name, locale=locale, currency=currency)

@component(Categories)
def categories(categories: Categories,
):
    try:
        hook = callbacks.categories
    except AttributeError:
        return None
    return hook(categories)

@typedlist(Category)
def category(*args):
    return None

@component(Category)
def category_component(category_component: Category,
    id: Identifier,
    name: str,
    parent_id: Identifier | None = None,
):
    try:
        hook = callbacks.category_component
    except AttributeError:
        return None
    return hook(category_component, id=id, name=name, parent_id=parent_id)

@component(Products)
def products(products: Products,
):
    try:
        hook = callbacks.products
    except AttributeError:
        return None
    return hook(products)

@typedlist(Product)
def product(*args):
    return None

@component(Product)
def product_component(product_component: Product,
):
    try:
        hook = callbacks.product_component
    except AttributeError:
        return None
    return hook(product_component)

@component(ProductIdentity)
def identity(identity: ProductIdentity,
    sku: Sku,
    name: str,
    description: str | None = None,
    brand: str | None = None,
):
    try:
        hook = callbacks.identity
    except AttributeError:
        return None
    return hook(identity, sku=sku, name=name, description=description, brand=brand)

@component(Variants)
def variants(variants: Variants,
):
    try:
        hook = callbacks.variants
    except AttributeError:
        return None
    return hook(variants)

@typedlist(Variant)
def variant(*args):
    return None

@component(Variant)
def variant_component(variant_component: Variant,
    sku: Sku,
):
    try:
        hook = callbacks.variant_component
    except AttributeError:
        return None
    return hook(variant_component, sku=sku)

@component(Price)
def price(price: Price,
    amount: float,
    currency: Currency,
):
    try:
        hook = callbacks.price
    except AttributeError:
        return None
    return hook(price, amount=amount, currency=currency)

@component(Attributes)
def attributes(attributes: Attributes,
):
    try:
        hook = callbacks.attributes
    except AttributeError:
        return None
    return hook(attributes)

@typedlist(Attribute)
def attribute(*args):
    return None

@component(Attribute)
def attribute_component(attribute_component: Attribute,
    name: str,
    value: str,
):
    try:
        hook = callbacks.attribute_component
    except AttributeError:
        return None
    return hook(attribute_component, name=name, value=value)

@component(Inventory)
def inventory(inventory: Inventory,
    quantity: int,
    availability: str | Availability,
):
    try:
        hook = callbacks.inventory
    except AttributeError:
        return None
    return hook(inventory, quantity=quantity, availability=availability)

@component(CategoryRefs)
def category_refs(category_refs: CategoryRefs,
    category_ref: list[Identifier],
):
    try:
        hook = callbacks.category_refs
    except AttributeError:
        return None
    return hook(category_refs, category_ref=category_ref)

@component(MediaItems)
def media(media: MediaItems,
):
    try:
        hook = callbacks.media
    except AttributeError:
        return None
    return hook(media)

@typedlist(Media)
def media(*args):
    return None

@component(Media)
def media_component(media_component: Media,
    url: str,
    kind: str | MediaKind,
    alt_text: str | None = None,
):
    try:
        hook = callbacks.media_component
    except AttributeError:
        return None
    return hook(media_component, url=url, kind=kind, alt_text=alt_text)

@component(Fulfillment)
def fulfillment(fulfillment: Fulfillment,
    requires_shipping: bool,
    returnable: bool,
    weight_grams: int | None = None,
):
    try:
        hook = callbacks.fulfillment
    except AttributeError:
        return None
    return hook(fulfillment, requires_shipping=requires_shipping, returnable=returnable, weight_grams=weight_grams)

@component(SubmissionOptions)
def submission_options(submission_options: SubmissionOptions,
    mode: str | SubmissionMode,
    dry_run: bool | None = None,
):
    try:
        hook = callbacks.submission_options
    except AttributeError:
        return None
    return hook(submission_options, mode=mode, dry_run=dry_run)

