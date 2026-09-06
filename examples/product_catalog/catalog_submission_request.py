from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
from product_catalog import MediaItems, Product, Fulfillment, Attributes, Inventory, Categories, Locale, SubmissionOptions, Media, Availability, Products, Category, Catalog, MediaKind, ProductIdentity, Attribute, CategoryRefs, Variant, Sku, SubmissionMode, CatalogSubmissionRequest, Price, Variants, Identifier, Currency
from pylib.decorators import typedlist, component

#--------------------------------------------------------------------------------------------------------------
#                                           CatalogSubmissionRequest:CatalogSubmissionRequest                                           
#--------------------------------------------------------------------------------------------------------------
@component(CatalogSubmissionRequest)
def catalog_submission_request(
    catalog_submission_request:CatalogSubmissionRequest,
):
    pass
#--------------------------------------------------------------------------------------------------------------
#                                                    CatalogSubmissionRequest:Catalog                                                    
#--------------------------------------------------------------------------------------------------------------
@component(Catalog)
def catalog(
    catalog:Catalog,
    name:str,
    locale:Locale,
    currency:Currency,
):
    """
    the element is populated as:
    catalog(
        name = name_value # mandatory
        locale = locale_value # mandatory
        currency = currency_value # mandatory
    )

    the element nested element(s) are added as:
    catalog.categories # optional

    the element population operation returns a reference to the catalog element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: name=%s,locale=%s,currency=%s',
    name, locale, currency)

    logger.debug('committed message properties: name=%s, locale=%s, currency=%s',
    catalog.name, catalog.locale, catalog.currency)
#--------------------------------------------------------------------------------------------------------------
#                                                  CatalogSubmissionRequest:Categories                                                  
#--------------------------------------------------------------------------------------------------------------
@component(Categories)
def categories(
    categories:Categories,
):
    """

    the element nested element(s) are added as:
    categories.category # optional

    the element population operation returns a reference to the categories element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:category                                                   
#--------------------------------------------------------------------------------------------------------------
@typedlist(Category)
def category(*args):
    """
    category list element contains category elements

    there are several ways to add an element to a list:
    list_element_ref = category(category(...))
    category.category_alias(...)
    """

    logger.debug("submitted list element(s): %s", args)
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:Category                                                   
#--------------------------------------------------------------------------------------------------------------
@component(Category)
def category(
    category:Category,
    id:Identifier,
    name:str,
    parent_id:Identifier | None=None,
):
    """
    the element is populated as:
    category(
        id = id_value # mandatory
        name = name_value # mandatory
        parent_id = parent_id_value # optional
    )
    the element population operation returns a reference to the category element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: id=%s,name=%s,parent_id=%s',
    id, name, parent_id)

    logger.debug('committed message properties: id=%s, name=%s, parent_id=%s',
    category.id, category.name, category.parent_id)
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:Products                                                   
#--------------------------------------------------------------------------------------------------------------
@component(Products)
def products(
    products:Products,
):
    """

    the element nested element(s) are added as:
    products.product # optional

    the element population operation returns a reference to the products element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                    CatalogSubmissionRequest:product                                                    
#--------------------------------------------------------------------------------------------------------------
@typedlist(Product)
def product(*args):
    """
    product list element contains product elements

    there are several ways to add an element to a list:
    list_element_ref = product(product(...))
    product.product_alias(...)
    """

    logger.debug("submitted list element(s): %s", args)
#--------------------------------------------------------------------------------------------------------------
#                                                    CatalogSubmissionRequest:Product                                                    
#--------------------------------------------------------------------------------------------------------------
@component(Product)
def product(
    product:Product,
):
    """

    the element nested element(s) are added as:
    product.identity # optional
    product.variants # optional
    product.category_refs # optional
    product.media # optional
    product.attributes # optional
    product.fulfillment # optional

    the element population operation returns a reference to the product element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                CatalogSubmissionRequest:ProductIdentity                                                
#--------------------------------------------------------------------------------------------------------------
@component(ProductIdentity)
def identity(
    identity:ProductIdentity,
    sku:Sku,
    name:str,
    description:str | None=None,
    brand:str | None=None,
):
    """
    the element is populated as:
    product_identity(
        sku = sku_value # mandatory
        name = name_value # mandatory
        description = description_value # optional
        brand = brand_value # optional
    )
    the element population operation returns a reference to the product_identity element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: sku=%s,name=%s,description=%s,brand=%s',
    sku, name, description, brand)

    logger.debug('committed message properties: sku=%s, name=%s, description=%s, brand=%s',
    product_identity.sku, product_identity.name, product_identity.description, product_identity.brand)
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:Variants                                                   
#--------------------------------------------------------------------------------------------------------------
@component(Variants)
def variants(
    variants:Variants,
):
    """

    the element nested element(s) are added as:
    variants.variant # optional

    the element population operation returns a reference to the variants element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                    CatalogSubmissionRequest:variant                                                    
#--------------------------------------------------------------------------------------------------------------
@typedlist(Variant)
def variant(*args):
    """
    variant list element contains variant elements

    there are several ways to add an element to a list:
    list_element_ref = variant(variant(...))
    variant.variant_alias(...)
    """

    logger.debug("submitted list element(s): %s", args)
#--------------------------------------------------------------------------------------------------------------
#                                                    CatalogSubmissionRequest:Variant                                                    
#--------------------------------------------------------------------------------------------------------------
@component(Variant)
def variant(
    variant:Variant,
    sku:Sku,
):
    """
    the element is populated as:
    variant(
        sku = sku_value # mandatory
    )

    the element nested element(s) are added as:
    variant.price # optional
    variant.attributes # optional
    variant.inventory # optional

    the element population operation returns a reference to the variant element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: sku=%s',
    sku)

    logger.debug('committed message properties: sku=%s',
    variant.sku)
#--------------------------------------------------------------------------------------------------------------
#                                                     CatalogSubmissionRequest:Price                                                     
#--------------------------------------------------------------------------------------------------------------
@component(Price)
def price(
    price:Price,
    amount:float,
    currency:Currency,
):
    """
    the element is populated as:
    price(
        amount = amount_value # mandatory
        currency = currency_value # mandatory
    )
    the element population operation returns a reference to the price element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: amount=%s,currency=%s',
    amount, currency)

    logger.debug('committed message properties: amount=%s, currency=%s',
    price.amount, price.currency)
#--------------------------------------------------------------------------------------------------------------
#                                                  CatalogSubmissionRequest:Attributes                                                  
#--------------------------------------------------------------------------------------------------------------
@component(Attributes)
def attributes(
    attributes:Attributes,
):
    """

    the element nested element(s) are added as:
    attributes.attribute # optional

    the element population operation returns a reference to the attributes element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:attribute                                                   
#--------------------------------------------------------------------------------------------------------------
@typedlist(Attribute)
def attribute(*args):
    """
    attribute list element contains attribute elements

    there are several ways to add an element to a list:
    list_element_ref = attribute(attribute(...))
    attribute.attribute_alias(...)
    """

    logger.debug("submitted list element(s): %s", args)
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:Attribute                                                   
#--------------------------------------------------------------------------------------------------------------
@component(Attribute)
def attribute(
    attribute:Attribute,
    name:str,
    value:str,
):
    """
    the element is populated as:
    attribute(
        name = name_value # mandatory
        value = value_value # mandatory
    )
    the element population operation returns a reference to the attribute element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: name=%s,value=%s',
    name, value)

    logger.debug('committed message properties: name=%s, value=%s',
    attribute.name, attribute.value)
#--------------------------------------------------------------------------------------------------------------
#                                                   CatalogSubmissionRequest:Inventory                                                   
#--------------------------------------------------------------------------------------------------------------
@component(Inventory)
def inventory(
    inventory:Inventory,
    quantity:int,
    availability:str | Availability,
):
    """
    the element is populated as:
    inventory(
        quantity = quantity_value # mandatory
        availability = availability_value # mandatory
    )
    the element population operation returns a reference to the inventory element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: quantity=%s,availability=%s',
    quantity, availability)

    logger.debug('committed message properties: quantity=%s, availability=%s',
    inventory.quantity, inventory.availability)
#--------------------------------------------------------------------------------------------------------------
#                                                 CatalogSubmissionRequest:CategoryRefs                                                 
#--------------------------------------------------------------------------------------------------------------
@component(CategoryRefs)
def category_refs(
    category_refs:CategoryRefs,
    category_ref:list,
):
    """
    the element is populated as:
    category_refs(
        category_ref = category_ref_value # mandatory
    )
    the element population operation returns a reference to the category_refs element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: category_ref=%s',
    category_ref)

    logger.debug('committed message properties: category_ref=%s',
    category_refs.category_ref)
#--------------------------------------------------------------------------------------------------------------
#                                                  CatalogSubmissionRequest:MediaItems                                                  
#--------------------------------------------------------------------------------------------------------------
@component(MediaItems)
def media(
    media:MediaItems,
):
    """

    the element nested element(s) are added as:
    media_items.media # optional

    the element population operation returns a reference to the media_items element instance
    the element nested element addition operation returns a reference to added element
    """


    pass
#--------------------------------------------------------------------------------------------------------------
#                                                     CatalogSubmissionRequest:media                                                     
#--------------------------------------------------------------------------------------------------------------
@typedlist(Media)
def media(*args):
    """
    media list element contains media elements

    there are several ways to add an element to a list:
    list_element_ref = media(media(...))
    media.media_alias(...)
    """

    logger.debug("submitted list element(s): %s", args)
#--------------------------------------------------------------------------------------------------------------
#                                                     CatalogSubmissionRequest:Media                                                     
#--------------------------------------------------------------------------------------------------------------
@component(Media)
def media(
    media:Media,
    url:str,
    kind:str | MediaKind,
    alt_text:str | None=None,
):
    """
    the element is populated as:
    media(
        url = url_value # mandatory
        kind = kind_value # mandatory
        alt_text = alt_text_value # optional
    )
    the element population operation returns a reference to the media element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: url=%s,kind=%s,alt_text=%s',
    url, kind, alt_text)

    logger.debug('committed message properties: url=%s, kind=%s, alt_text=%s',
    media.url, media.kind, media.alt_text)
#--------------------------------------------------------------------------------------------------------------
#                                                  CatalogSubmissionRequest:Fulfillment                                                  
#--------------------------------------------------------------------------------------------------------------
@component(Fulfillment)
def fulfillment(
    fulfillment:Fulfillment,
    requires_shipping:bool,
    returnable:bool,
    weight_grams:int | None=None,
):
    """
    the element is populated as:
    fulfillment(
        requires_shipping = requires_shipping_value # mandatory
        returnable = returnable_value # mandatory
        weight_grams = weight_grams_value # optional
    )
    the element population operation returns a reference to the fulfillment element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: requires_shipping=%s,returnable=%s,weight_grams=%s',
    requires_shipping, returnable, weight_grams)

    logger.debug('committed message properties: requires_shipping=%s, returnable=%s, weight_grams=%s',
    fulfillment.requires_shipping, fulfillment.returnable, fulfillment.weight_grams)
#--------------------------------------------------------------------------------------------------------------
#                                               CatalogSubmissionRequest:SubmissionOptions                                               
#--------------------------------------------------------------------------------------------------------------
@component(SubmissionOptions)
def submission_options(
    submission_options:SubmissionOptions,
    mode:str | SubmissionMode,
    dry_run:bool | None=None,
):
    """
    the element is populated as:
    submission_options(
        mode = mode_value # mandatory
        dry_run = dry_run_value # optional
    )
    the element population operation returns a reference to the submission_options element instance
    the element nested element addition operation returns a reference to added element
    """


    logger.debug('submitted parameters: mode=%s,dry_run=%s',
    mode, dry_run)

    logger.debug('committed message properties: mode=%s, dry_run=%s',
    submission_options.mode, submission_options.dry_run)
