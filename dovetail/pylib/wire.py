"""Utilities for converting wire dictionaries into generated components."""

import enum
import importlib
from dataclasses import fields, is_dataclass
from typing import Any, get_args, get_origin, get_type_hints


def camel_to_snake(name: str) -> str:
    """Convert a schema field name to the generated Python field name."""
    return ''.join('_' + character.lower() if character.isupper() else character for character in name).lstrip('_')


def _coerce(value: Any, annotation: Any) -> Any:
    """Coerce a wire value to an enum, scalar, optional, or list value."""
    if value is None:
        return None
    if get_origin(annotation) is list:
        item_type = get_args(annotation)[0]
        return [_coerce(item, item_type) for item in value]
    if get_origin(annotation) is not None and type(None) in get_args(annotation):
        types = [item for item in get_args(annotation) if item is not type(None)]
        for item_type in types:
            try:
                return _coerce(value, item_type)
            except (TypeError, ValueError):
                continue
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return annotation(value)
    if annotation in (str, int, float, bool):
        return annotation(value)
    return value


def wire_to_component(
    wire: dict[str, Any],
    module_name: str,
    factory_name: str,
    root_key: str | None = None,
) -> Any:
    """Deserialize a wire dictionary into a generated decorated component.

    Args:
        wire: Wire payload, optionally wrapped by ``root_key``.
        module_name: Module containing the generated component factory.
        factory_name: Generated factory name, such as
            ``catalog_submission_response``.
        root_key: Optional wire envelope key to unwrap before conversion.

    Returns:
        A populated generated component instance.
    """
    # Unwrap a protocol envelope before matching its fields to the generated
    # component's dataclass definition.
    payload = wire[root_key] if root_key is not None else wire
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name)
    component_type = type(factory)
    type_hints = get_type_hints(component_type)
    scalar_values = {}
    nested_values = []

    for field in fields(component_type):
        wire_name = field.name
        if wire_name not in payload:
            wire_name = next(
                (name for name in payload if camel_to_snake(name) == field.name),
                None,
            )
        if wire_name is None:
            continue
        annotation = type_hints.get(field.name, field.type)
        value = payload[wire_name]
        if isinstance(value, dict):
            nested_values.append((field, value, annotation))
        elif isinstance(value, list):
            nested_values.append((field, value, annotation))
        else:
            scalar_values[camel_to_snake(field.name)] = _coerce(value, annotation)

    # Populate scalars through the generated factory so its component hook is
    # invoked; attach nested values afterward through the component fields.
    instance = factory(**scalar_values)
    for field, value, annotation in nested_values:
        nested_type = next(
            (item for item in get_args(annotation) if item is not type(None)),
            annotation,
        )
        if get_origin(nested_type) is list:
            nested_type = get_args(nested_type)[0]
            list_factory = getattr(instance, f"{field.name}")
            item_factory_name = f"{camel_to_snake(nested_type.__name__)}_component"
            item_factory = getattr(module, item_factory_name)
            for item in value:
                list_factory(wire_to_component(item, module_name, item_factory_name))
        elif is_dataclass(nested_type):
            nested_factory_name = camel_to_snake(nested_type.__name__)
            nested = wire_to_component(value, module_name, nested_factory_name)
            setattr(instance, field.name, nested)
    return instance
