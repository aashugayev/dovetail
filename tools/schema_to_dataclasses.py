"""Generate Python dataclasses from a practical subset of XSD schemas.

The generator intentionally defers these advanced XSD features:

* ``xs:include`` and ``xs:import`` across multiple schema files.
* Identity constraints such as ``xs:key`` and ``xs:keyref``.
* Substitution groups and abstract schema types.
* ``xs:union`` and ``xs:list`` simple types.
* Full ``xs:choice`` cardinality and mutual-exclusion semantics.
"""

import os
import re
import sys
import logging
import argparse
import json
from collections.abc import Mapping
from lxml import etree
from collections import defaultdict

logging.basicConfig(format="%(levelname)s::[%(lineno)d] - %(message)s")
logging.getLogger().setLevel(logging.DEBUG)

enum_dict = defaultdict(list)
simple_type_dict = {}
class_dict = defaultdict(list)
class_set = set()

COMPLEX_TYPE = "complexType"
SIMPLE_TYPE = "simpleType"
SEQUENCE = "sequence"
ELEMENT = "element"
CHOICE = "choice"
ALL = "all"
ATTRIBUTE = "attribute"
ANNOTATION = "annotation"
COMPLEX_CONTENT = "complexContent"
EXTENSION = "extension"
RESTRICTION = "restriction"
ENUMERATION = "enumeration"
MIN_OCCURS = "minOccurs"
MAX_OCCURS = "maxOccurs"
OCCURS_ZERO = "0"
OCCURS_ONE = "1"
NAME = "name"
TYPE = "type"
VALUE = "value"
BASE = "base"
DEFAULT = "default"
FIXED = "fixed"
USE = "use"
REQUIRED = "required"
NILLABLE = "nillable"
TRUE = "true"
ENUM_FIELD_PATTERN = re.compile(r".*\[\'?([a-zA-Z0-9_]+)\'?\].*|\'?([a-zA-Z0-9_]+)\'?")

module_imports = """
from __future__ import annotations
from typing import get_type_hints, get_args
from dataclasses import dataclass
from datetime import date
import enum
import re
"""

check_enum = """
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
"""

enum_post_init = """
    def __post_init__(self):
        for enum in ({},):
            check_enum(self, enum)
"""

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'xsd_to_py_class.json')
type_xml_to_py = {}
xsd_namespaces = set()
complex_type_namespaces = set()
IS_CAMEL_TO_SNAKE = False


def load_config(config_file: str = CONFIG_FILE) -> None:
    """Load type mappings, namespaces, and naming options from a JSON file."""
    global type_xml_to_py, xsd_namespaces, complex_type_namespaces, IS_CAMEL_TO_SNAKE

    with open(config_file, encoding='utf-8') as file:
        config = json.load(file)
    type_xml_to_py = config['type_xml_to_py']
    xsd_namespaces = set(config['xsd_namespaces'])
    complex_type_namespaces = set(config['complex_type_namespaces'])
    IS_CAMEL_TO_SNAKE = config.get('is_camel_to_snake', False)
 
def cammel_to_snake(cammel: str) -> str:
    """Convert a CamelCase name to snake_case when configured to do so."""
    if IS_CAMEL_TO_SNAKE: 
        snake = ''.join(['_'+i.lower() if i.isupper() 
            else i for i in cammel]).lstrip('_')
        return snake
    return cammel


def is_xml_element(element: str, local_name: str) -> bool:
    """Return whether an XML tag has the specified local name."""
    return etree.QName(element).localname == local_name


def annotate(
    attrib: Mapping[str, str],
    optional: bool = False,
    type_: str = '',
    value: str = '',
) -> str | None:
    """
    Annotate an XML schema attribute with its Python type and optionality.

    Args:
        attrib: XML schema attribute data.
        optional: Whether the generated field should be optional.
        type_: Initial type for attributes without a ``type`` key.
        value: Default value appended to the generated annotation.

    Returns:
        The generated field annotation, or ``None`` when no field name exists.
    """
    annotation = attrib.get(NAME) or attrib.get(VALUE)
    if annotation is None:
        logging.info(f"Missing 'name' or 'value' in attribute: {attrib}")
        return None
    
    is_list = False # set is_list flag to False initially

    if TYPE in attrib:
        type_ = attrib.get(TYPE)
        (space, _type) = type_.split(':')
        if space in xsd_namespaces:
            if _type in type_xml_to_py:
                type_ = type_xml_to_py[_type]
            else:
                logging.error(f"unknown {space}:{_type}")
        elif space in complex_type_namespaces:
            type_ = _type
        else:
            logging.error(f"unknown namespace {space} for type {_type}")

        if MAX_OCCURS in attrib and attrib[MAX_OCCURS] != OCCURS_ONE:
            is_list = True
            type_ = f'list[{type_}]'    
        if MIN_OCCURS in attrib:
            if attrib[MIN_OCCURS] == OCCURS_ZERO:
                optional = True
            elif is_list:
                value = '' # '= []' is incorrect - should parse minOccurs and maxOccurs and use 3.9 https://docs.python.org/3/library/typing.html#typing.Annotated
        if NILLABLE in attrib and attrib[NILLABLE] == TRUE:
            type_ = f'{type_} | None'
            value = ' = None'

        default = attrib.get(DEFAULT) or attrib.get(FIXED)
        if default is not None:
            optional = False
            value = repr(default)

        if optional and default is None:
            type_ = f'{type_} | None'
            value = ' = None'
        
    type_ = f'{type_}{value}'
           
    return f'{cammel_to_snake(annotation)}:{type_}'   
            
def parse_args() -> argparse.Namespace:
    """Parse command-line options for schema and dataclass generation."""

    this_dir = os.path.dirname(__file__)
    schema_dir = os.path.join(this_dir, os.path.pardir, 'schema')
    apilib_dir = os.path.join(this_dir, os.path.pardir, 'dovetail')
    
    parser = argparse.ArgumentParser(allow_abbrev=True)
    parser.add_argument("--schema_file", type=str, default=f"{schema_dir}/pepapi.xml", help="schema file location")
    parser.add_argument("--classes_file", type=str, default=f"{apilib_dir}/pepapi.py", help="dataclasses file location")
    parser.add_argument("--logging_level", type=str, default="DEBUG", help="dataclasses file location")
    parser.add_argument("--write_to_file", action='store_true', help="write dataclasses to file")
    parser.add_argument("--config_file", type=str, default=CONFIG_FILE, help="type mapping and namespace config file")
    args = parser.parse_args()
    return args

def gen_classes(
    schema_file: str,
    classes_file: str,
    is_write_to_file: bool = False,
) -> None:
    """Generate Python dataclass source from an XML schema file.

    Args:
        schema_file: Path to the XML schema.
        classes_file: Output path when ``is_write_to_file`` is enabled.
        is_write_to_file: Whether to write generated source to ``classes_file``.
    """
        
    tree = etree.parse(schema_file)
    root = tree.getroot()
    for child in root:

        if is_xml_element(child.tag, COMPLEX_TYPE):
            logging.debug("%s %s", COMPLEX_TYPE.upper(), child.attrib)
            class_name = child.attrib[NAME]
            class_def = class_dict[class_name]
            model_parent = child
            base_class = None
            for candidate in child:
                if is_xml_element(candidate.tag, COMPLEX_CONTENT):
                    for content in candidate:
                        if is_xml_element(content.tag, EXTENSION):
                            model_parent = content
                            base_class = content.attrib.get(BASE)
                            break
            class_header = f"class {class_name}"
            if base_class:
                class_header += f"({base_class.split(':', 1)[-1]})"
            class_def.append(f"{class_header}:")
            class_set.add(class_name)
            for grandchild in model_parent:

                if is_xml_element(grandchild.tag, SEQUENCE) or is_xml_element(grandchild.tag, ALL):
                    logging.debug("    %s %s", SEQUENCE.upper(), grandchild.attrib)
                    mandatory_fields = []
                    optional_fields = []
                    for sequence in grandchild:
                        if is_xml_element(sequence.tag, ELEMENT):
                            logging.debug("        %s %s", ELEMENT.upper(), sequence.attrib)
                            annotation = annotate(sequence.attrib)
                            if ' | None' in annotation:
                                optional_fields.append(f"    {annotation}")
                            else:
                                mandatory_fields.append(f"    {annotation}")
                    class_def.extend(mandatory_fields)
                    class_def.extend(optional_fields)

                elif is_xml_element(grandchild.tag, CHOICE):
                    logging.debug("    %s %s", CHOICE.upper(), grandchild.attrib)
                    for choice in grandchild:
                        if is_xml_element(choice.tag, ELEMENT):
                            logging.debug("        %s %s", ELEMENT.upper(), choice.attrib)
                            annotation = annotate(choice.attrib, optional=True)
                            class_def.append(f"    {annotation}")
                elif is_xml_element(grandchild.tag, ATTRIBUTE):
                    logging.debug("    %s %s", ATTRIBUTE.upper(), grandchild.attrib)
                    annotation = annotate(
                        grandchild.attrib,
                        optional=grandchild.attrib.get(USE) != REQUIRED,
                    )
                    if annotation is not None:
                        class_def.append(f"    {annotation}")
                elif is_xml_element(grandchild.tag, ANNOTATION):
                    for annotation in grandchild:
                        logging.debug("        COMMENT %s", annotation.text)
                else:
                    logging.error("    UNKNOWN %s %s", grandchild.tag, grandchild.attrib)
        elif is_xml_element(child.tag, SIMPLE_TYPE):
            logging.debug("%s %s", SIMPLE_TYPE.upper().replace("_", ""), child.attrib)
            for grandchild in child:
                if is_xml_element(grandchild.tag, RESTRICTION):
                    logging.debug("    RESTRICTION %s", grandchild.attrib)
                    enum_restrictions = [
                        restriction
                        for restriction in grandchild
                        if is_xml_element(restriction.tag, ENUMERATION)
                    ]
                    type_name = child.attrib[NAME]
                    base_type = grandchild.attrib[BASE].split(':', 1)[-1]
                    if enum_restrictions:
                        enum_dict[type_name].append(f"class {type_name}(enum.Enum):")
                    else:
                        simple_type_dict[type_name] = {
                            'base': type_xml_to_py.get(base_type, base_type),
                            'facets': [
                                (etree.QName(facet.tag).localname, facet.attrib[VALUE])
                                for facet in grandchild
                                if VALUE in facet.attrib
                            ],
                        }
                    class_set.add(type_name)
                    for value, restriction in enumerate(enum_restrictions):
                        if is_xml_element(restriction.tag, ENUMERATION):
                            logging.debug("        %s %s", ENUMERATION.upper(), restriction.attrib)
                            annotation = annotate(
                                restriction.attrib,
                                type_=type_xml_to_py.get(base_type, base_type),
                                value=f" = {restriction.attrib[VALUE]!r}",
                            )
                            enum_dict[type_name].append(f"    {annotation}")
    
    enum_registry = dict()
    enum_fields = defaultdict(list)

    for class_name, class_def in class_dict.items():
        for line_num, class_code in enumerate(class_def):
            if not line_num:
                class_def[line_num] = "@dataclass\n" + class_code
                continue
            tokens = [token.strip() for token in re.split(':|=', class_code)]
            match = ENUM_FIELD_PATTERN.match(tokens[1])
            if match:
                token = match.group(1) or match.group(2)
                if token in enum_dict:
                    logging.debug("matched enum field=%s", token)
                    class_def[line_num] = f"    {tokens[0]}:" + re.sub(
                        f"\\'?{token}\\'?", f"str | {token}", tokens[1], count=1
                    ) + ('=' + tokens[2] if len(tokens) > 2 else '')
                    enum_registry.setdefault(token, True)
                    enum_fields[class_name].append(tokens[0])
    
    if is_write_to_file:
        stdout = sys.stdout
        file = open(classes_file, "w")
        sys.stdout = file
        
    print(module_imports)
    print('\n')
    print(check_enum)
    print('\n')
    print("pepapi_import = [")
    for cls in list(class_set):
        print(f'    "{cls}",')
    print("]")
    
    print('\n'*2)
    for type_name, type_definition in simple_type_dict.items():
        base_type = type_definition['base']
        print(f"class {type_name}({base_type}):")
        print(f"    def __new__(cls, value: {base_type}) -> \"{type_name}\":")
        print(f"        value = {base_type}(value)")
        for facet, value in type_definition['facets']:
            if facet == 'minLength':
                print(f"        if len(value) < {value}:")
                print(f"            raise ValueError(f'{{cls.__name__}} must contain at least {value} characters')")
            elif facet == 'maxLength':
                print(f"        if len(value) > {value}:")
                print(f"            raise ValueError(f'{{cls.__name__}} must contain at most {value} characters')")
            elif facet == 'length':
                print(f"        if len(value) != {value}:")
                print(f"            raise ValueError(f'{{cls.__name__}} must contain exactly {value} characters')")
            elif facet == 'pattern':
                print(f"        if re.fullmatch({value!r}, value) is None:")
                print(f"            raise ValueError(f'{{cls.__name__}} does not match the required pattern')")
            elif facet in {'minInclusive', 'maxInclusive', 'minExclusive', 'maxExclusive'}:
                comparison = {
                    'minInclusive': '<',
                    'maxInclusive': '>',
                    'minExclusive': '<=',
                    'maxExclusive': '>=',
                }[facet]
                print(f"        if value {comparison} {value}:")
                print(f"            raise ValueError(f'{{cls.__name__}} violates {facet}={value}')")
        print("        return super().__new__(cls, value)")
        print()

    if simple_type_dict:
        print('\n')

    for enum in enum_registry:
        print('\n')
        print('\n'.join(enum_dict[enum]))

    for class_key, class_def in class_dict.items():
        logging.debug("class name=%s", class_key)
        enum_list = enum_fields[class_key]
        if len(class_def) == 1:
            class_def.append("    pass")
            # continue
                
        print('\n')
        print('\n'.join(class_def))
        if (enum_list):
            print(enum_post_init.format(','.join([f'"{enum}"' for enum in enum_list])))
            
    if is_write_to_file:
        file.close()
        sys.stdout = stdout
        
if __name__ == "__main__":
    
    args = parse_args()
    load_config(args.config_file)
    logging.basicConfig(format="%(levelname)7s::%(name)s:%(funcName)10s:[%(lineno)3d] - %(message)s")
    logging.getLogger().setLevel(args.logging_level)
    logging.info(f"command line arguments={args}")
    
    gen_classes(args.schema_file, args.classes_file, is_write_to_file=args.write_to_file)