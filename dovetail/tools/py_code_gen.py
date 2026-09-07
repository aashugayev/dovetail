"""Generate callable component modules and extension-hook contracts from dataclasses."""

import argparse
import enum
import importlib
import logging
import os
import sys
import types
from collections import defaultdict
from dataclasses import fields, is_dataclass
from typing import Union, get_args, get_origin, get_type_hints


logging.basicConfig(format="%(levelname)7s::%(funcName)10s:[%(lineno)3d] - %(message)s")
logger = logging.getLogger(__name__)


def camel_to_snake(name: str) -> str:
    """Convert a CamelCase name to snake_case."""
    return ''.join('_' + character.lower() if character.isupper() else character for character in name).lstrip('_')


def resolved_type_hints(cls: type) -> dict[str, object]:
    """Resolve postponed and forward-referenced annotations for a dataclass.

    ``cls.__module__`` identifies the defining module. Its attributes provide
    the namespace used to evaluate generated postponed annotations, returning
    a mapping of field names to runtime type objects.
    """
    module = sys.modules.get(cls.__module__)
    namespace = vars(module) if module is not None else None
    return get_type_hints(cls, globalns=namespace, localns=namespace)


def is_union_type(annotation: object) -> bool:
    """Return whether an annotation is a typing or Python 3.10 union."""
    return get_origin(annotation) in (Union, types.UnionType)


def is_scalar_type(annotation: object) -> bool:
    """Return whether an annotation represents a scalar value."""
    return isinstance(annotation, type) and issubclass(annotation, (str, int, float, bool, bytes))


def is_builtin_scalar_type(annotation: object) -> bool:
    """Return whether an annotation is a built-in scalar type rather than a named schema subtype."""
    return annotation in (str, int, float, bool, bytes)


def add_annotation_imports(imports: set[str], annotation: object) -> None:
    """Add non-built-in types contained in an annotation to generated imports."""
    if is_union_type(annotation) or get_origin(annotation) is list:
        for item in get_args(annotation):
            add_annotation_imports(imports, item)
    elif annotation is not type(None) and not is_builtin_scalar_type(annotation):
        imports.add(annotation.__name__)


def unwrap_annotation(annotation: object) -> tuple[object, bool]:
    """Return an annotation's contained type and whether it is a list."""
    while is_union_type(annotation):
        annotation = next(item for item in get_args(annotation) if item is not type(None))
    if get_origin(annotation) is list:
        return get_args(annotation)[0], True
    return annotation, False


def format_annotation(annotation: object) -> str:
    """Format a resolved annotation for generated Python 3.10 signatures."""
    if annotation is type(None):
        return "None"
    if is_union_type(annotation):
        return " | ".join(format_annotation(item) for item in get_args(annotation))
    if get_origin(annotation) is list:
        return f"list[{format_annotation(get_args(annotation)[0])}]"
    return annotation.__name__


def callback_module_name(root_class: type) -> str:
    """Return the developer-owned callback module name for a root class."""
    return f"{camel_to_snake(root_class.__name__)}_callbacks"


def parse_args() -> argparse.Namespace:
    """Parse component-generation command-line options."""
    this_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--api_name", default="myapi", help="generated dataclass module name")
    parser.add_argument("--tmp_api_lib", default=os.path.join(this_dir, os.pardir, os.pardir, "_dovetail"), help="temporary component output directory")
    parser.add_argument("--api_lib", default=os.path.join(this_dir, os.pardir), help="directory containing the generated dataclass module")
    parser.add_argument("--request_class", default="Request", help="request root dataclass name")
    parser.add_argument("--response_class", default="", help="optional response root dataclass name")
    parser.add_argument("--logging_level", default="DEBUG", help="logging level")
    parser.add_argument("--write_to_file", action="store_true", help="write generated modules to files")
    return parser.parse_args()


def generate_root(root_class: type) -> tuple[dict[str, list[str]], set[str], dict[str, tuple[type, list[str]]]]:
    """Generate component source fragments, imports, and hook contracts for one root."""
    source: dict[str, list[str]] = defaultdict(list)
    imports: set[str] = set()
    hooks: dict[str, tuple[type, list[str]]] = {}
    emitted: set[tuple[type, str]] = set()

    def emit_component(cls: type, function_name: str) -> None:
        key = (cls, function_name)
        if key in emitted:
            return
        emitted.add(key)
        imports.add(cls.__name__)
        type_hints = resolved_type_hints(cls)
        scalar_fields = []
        nested_fields = []

        for field in fields(cls):
            annotation = type_hints[field.name]
            contained_type, is_list = unwrap_annotation(annotation)
            if is_scalar_type(contained_type) or (isinstance(contained_type, type) and issubclass(contained_type, enum.Enum)):
                scalar_fields.append((field, annotation))
                add_annotation_imports(imports, annotation)
            elif is_dataclass(contained_type):
                nested_fields.append((field.name, contained_type, is_list))
                imports.add(contained_type.__name__)

        source[function_name].append(f"@component({cls.__name__})")
        source[function_name].append(f"def {function_name}({function_name}: {cls.__name__},")
        for field, annotation in scalar_fields:
            default = " = None" if field.default is None else ""
            source[function_name].append(f"    {camel_to_snake(field.name)}: {format_annotation(annotation)}{default},")
        source[function_name].append("):")
        source[function_name].append("    try:")
        source[function_name].append(f"        hook = callbacks.{function_name}")
        source[function_name].append("    except AttributeError:")
        source[function_name].append("        return None")
        hook_arguments = ", ".join(
            f"{camel_to_snake(field.name)}={camel_to_snake(field.name)}" for field, _ in scalar_fields
        )
        suffix = f", {hook_arguments}" if hook_arguments else ""
        source[function_name].append(f"    return hook({function_name}{suffix})")
        source[function_name].append("")
        hooks[function_name] = (cls, [camel_to_snake(field.name) for field, _ in scalar_fields])

        for field_name, nested_type, is_list in nested_fields:
            nested_name = camel_to_snake(field_name)
            if is_list:
                source[nested_name].extend([
                    f"@typedlist({nested_type.__name__})",
                    f"def {nested_name}(*args):",
                    "    return None",
                    "",
                ])
            component_name = f"{nested_name}_component" if is_list else nested_name
            emit_component(nested_type, component_name)

    emit_component(root_class, camel_to_snake(root_class.__name__))
    return source, imports, hooks


def write_component_module(output_dir: str, api_name: str, root_class: type, source: dict[str, list[str]], imports: set[str]) -> None:
    """Write the generated component module for one request or response root."""
    path = os.path.join(output_dir, f"{camel_to_snake(root_class.__name__)}.py")
    with open(path, "w", encoding="utf-8") as file:
        file.write("from __future__ import annotations\n\n")
        file.write(f"from {api_name} import {', '.join(sorted(imports))}\n")
        file.write("from dovetail.pylib.decorators import typedlist, component\n")
        file.write(f"import {callback_module_name(root_class)} as callbacks\n\n")
        for lines in source.values():
            file.write("\n".join(lines))
            file.write("\n")


def write_callback_contracts(api_dir: str, roots: list[tuple[type, dict[str, tuple[type, list[str]]]]]) -> None:
    """Write generated contracts and create developer callback modules when absent."""
    generated_path = os.path.join(api_dir, "_generated_callbacks.py")
    with open(generated_path, "w", encoding="utf-8") as file:
        file.write('"""Generated callback contracts. Regenerated by py_code_gen.py."""\n\n')
        for root_class, hooks in roots:
            module_name = callback_module_name(root_class)
            file.write(f"# {module_name}\n")
            for hook_name, (_, parameters) in hooks.items():
                keyword_parameters = f", *, {', '.join(parameters)}" if parameters else ""
                file.write(f"def {hook_name}(component{keyword_parameters}):\n    return None\n\n")

            custom_path = os.path.join(api_dir, f"{module_name}.py")
            if not os.path.exists(custom_path):
                with open(custom_path, "w", encoding="utf-8") as custom_file:
                    custom_file.write(
                        '"""Developer-owned component enrichment hooks.\n\n'
                        'This file is created once and is never overwritten by py_code_gen.py.\n'
                        'See _generated_callbacks.py for current hook signatures.\n"""\n'
                    )


def main() -> None:
    """Generate component modules and callback contracts for configured root classes."""
    args = parse_args()
    logging.getLogger().setLevel(args.logging_level)
    sys.path.append(args.api_lib)
    api_module = importlib.import_module(args.api_name)
    roots = [getattr(api_module, args.request_class)]
    if args.response_class:
        roots.append(getattr(api_module, args.response_class))

    os.makedirs(args.tmp_api_lib, exist_ok=True)
    generated_roots = []
    for root_class in roots:
        source, imports, hooks = generate_root(root_class)
        if args.write_to_file:
            write_component_module(args.tmp_api_lib, args.api_name, root_class, source, imports)
        generated_roots.append((root_class, hooks))
    write_callback_contracts(args.api_lib, generated_roots)


if __name__ == "__main__":
    main()
