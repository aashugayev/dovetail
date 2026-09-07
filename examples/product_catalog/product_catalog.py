
from __future__ import annotations
from typing import get_type_hints, get_args
from dataclasses import dataclass
from datetime import date
import enum
import re




def check_enum(obj: object, enum: str) -> None:
    parameter = getattr(obj, enum)
    type_hints = get_type_hints(obj.__class__)[enum]
    args = get_args(type_hints)
    if type(parameter) is args[0]:
        try:
            args[1][parameter]
        except Exception as e:
            raise RuntimeError(f'{obj=}:{enum=}:{parameter=}:{type_hints=}:{args=}:exception={e}') from e
    elif type(parameter) is args[1]:
        try:
            parameter = parameter.name
        except Exception as e:
            raise RuntimeError(f'{obj=}:{enum=}:{parameter=}:{type_hints=}:{args=}:exception={e}') from e
    else:
        raise RuntimeError("Unknown type of %s.%s", obj.__class__.__name__, enum)



component_imports = [
    "Identifier",
    "Locale",
    "Sku",
    "Catalog",
    "Categories",
    "Inventory",
    "Currency",
    "Fulfillment",
    "Products",
    "CategoryRefs",
    "Category",
    "MediaItems",
    "CatalogSubmissionRequest",
    "Price",
    "ProductIdentity",
    "SubmissionStatus",
    "Product",
    "CatalogSubmissionResponse",
    "MediaKind",
    "Attributes",
    "Variant",
    "SubmissionOptions",
    "Media",
    "Availability",
    "Attribute",
    "Variants",
    "SubmissionMode",
]



class Identifier(str):
    def __new__(cls, value: str) -> "Identifier":
        value = str(value)
        if len(value) < 1:
            raise ValueError(f'{cls.__name__} must contain at least 1 characters')
        return super().__new__(cls, value)

class Sku(str):
    def __new__(cls, value: str) -> "Sku":
        value = str(value)
        if re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{1,63}', value) is None:
            raise ValueError(f'{cls.__name__} does not match the required pattern')
        return super().__new__(cls, value)

class Locale(str):
    def __new__(cls, value: str) -> "Locale":
        value = str(value)
        if re.fullmatch('[a-z]{2}(-[A-Z]{2})?', value) is None:
            raise ValueError(f'{cls.__name__} does not match the required pattern')
        return super().__new__(cls, value)

class Currency(str):
    def __new__(cls, value: str) -> "Currency":
        value = str(value)
        if re.fullmatch('[A-Z]{3}', value) is None:
            raise ValueError(f'{cls.__name__} does not match the required pattern')
        return super().__new__(cls, value)





class SubmissionStatus(enum.Enum):
    accepted:str = 'accepted'
    completed:str = 'completed'
    rejected:str = 'rejected'


class Availability(enum.Enum):
    in_stock:str = 'in_stock'
    backorder:str = 'backorder'
    out_of_stock:str = 'out_of_stock'


class MediaKind(enum.Enum):
    image:str = 'image'
    video:str = 'video'
    document:str = 'document'


class SubmissionMode(enum.Enum):
    upsert:str = 'upsert'
    replace:str = 'replace'


@dataclass
class CatalogSubmissionRequest:
    catalog:Catalog
    products:Products
    submissionOptions:SubmissionOptions | None = None


@dataclass
class CatalogSubmissionResponse:
    submissionId:str
    status:str | SubmissionStatus
    acceptedProducts:int
    rejectedProducts:int
    message:str | None = None

    def __post_init__(self):
        for enum in ("status",):
            check_enum(self, enum)



@dataclass
class Catalog:
    name:str
    locale:Locale
    currency:Currency
    categories:Categories | None = None


@dataclass
class Categories:
    category:list[Category]


@dataclass
class Category:
    id:Identifier
    name:str
    parentId:Identifier | None = None


@dataclass
class Products:
    product:list[Product]


@dataclass
class Product:
    identity:ProductIdentity
    variants:Variants
    categoryRefs:CategoryRefs | None = None
    media:MediaItems | None = None
    attributes:Attributes | None = None
    fulfillment:Fulfillment | None = None


@dataclass
class ProductIdentity:
    sku:Sku
    name:str
    description:str | None = None
    brand:str | None = None


@dataclass
class Variants:
    variant:list[Variant]


@dataclass
class Variant:
    sku:Sku
    price:Price
    attributes:Attributes | None = None
    inventory:Inventory | None = None


@dataclass
class Attributes:
    attribute:list[Attribute]


@dataclass
class Attribute:
    name:str
    value:str


@dataclass
class Price:
    amount:float
    currency:Currency


@dataclass
class Inventory:
    quantity:int
    availability:str | Availability

    def __post_init__(self):
        for enum in ("availability",):
            check_enum(self, enum)



@dataclass
class MediaItems:
    media:list[Media]


@dataclass
class Media:
    url:str
    kind:str | MediaKind
    altText:str | None = None

    def __post_init__(self):
        for enum in ("kind",):
            check_enum(self, enum)



@dataclass
class CategoryRefs:
    categoryRef:list[Identifier]


@dataclass
class Fulfillment:
    requiresShipping:bool
    returnable:bool
    weightGrams:int | None = None


@dataclass
class SubmissionOptions:
    mode:str | SubmissionMode
    dryRun:bool | None = None

    def __post_init__(self):
        for enum in ("mode",):
            check_enum(self, enum)

