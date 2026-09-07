import logging
logger = logging.getLogger(__name__)

import enum
import os
import sys
from inspect import isfunction
from dataclasses import fields, replace, asdict
from typing import Union, Callable, Generator, Any

is_trace_gbl = os.environ.get('TRACE', 'off').lower() in ('on', 'true', 'yes')

def camel_to_snake(camel:str)->str:
    """
    convert camelback string to snake string
    """
    snake = ''.join(['_'+i.lower() if i.isupper() else i for i in camel]).lstrip('_')
    return snake


def snake_to_camel(snake:str)->str:
    """
    convert snake string to camelback string
    """
    camel = ''.join([(i.capitalize() if n else i) for n, i in enumerate(snake.split('_'))])
    return camel


class typedlist:
    """Factory for a list that enforces element types and supports aliases.

    A generated ``@typedlist(Item)`` function is replaced with an instance of
    the returned list class. Calling it appends an independently assembled
    item; accessing an unknown attribute creates and names a new item wrapper.
    """
    def __new__(self, cls):
        """Create a typed-list class for instances of ``cls``."""
        logger.debug("generating %s typed list class instance", cls.__name__)
        class TypedList(list):
            """typed list class extension"""
            def __init__(self, arg:Union[Callable, Generator]):
                """Initialize an API wrapper or materialize a list generator."""
                if isfunction(arg):
                    logger.debug("initializing as a wrapper over method=%s", arg.__qualname__)
                    self.api_function = arg
                    self.api_module = self.api_function.__module__
                    self.__element_dict = dict()
                    self.__element_type = cls
                    self.__element_name = camel_to_snake(self.__element_type.__name__)
                    logger.debug("api module=%s::element name=%s", self.api_module, self.__element_name)
                else:
                    logger.debug("initializing with data generator=%s", arg)
                    super().__init__(arg)

            def __call__(self, *args):
                """Append typed elements and invoke the wrapped API function."""
                logger.debug("calling class=%s with args=%s", self.__class__.__name__, args)
                added = []
                for val in args:
                    replacement = replace(val)
                    self.append(replacement)
                    added.append(replacement)
                self.api_function(args)
                return added[-1] if added else self

            def __getattr__(self, name):
                """Return an alias or lazily create a named component item."""
                logger.debug("requesting name=%s", name)
                if name in self.__element_dict:
                    return self[self.__element_dict[name]]
                factory = getattr(sys.modules[self.api_module], f"{self.__element_name}_component")
                instance = type(factory)(factory.api_function)
                self.append(instance)
                self.__element_dict[name] = len(self) - 1
                return instance

            def append(self, element):
                """Append an item only when it has the declared element type."""
                if not isinstance(element, self.__element_type):
                    msg = f'Expected list member type={self.__element_type.__name__}::received list member type={type(element).__name__}'
                    logger.critical(msg)
                    raise TypeError(msg)
                list.append(self, element)

            def remove(self, name):
                """Remove and return every element registered under ``name``."""
                indexes = {
                    index for alias, index in self.__element_dict.items()
                    if alias == name
                }
                if not indexes:
                    return []

                # Delete from the end so earlier indexes remain valid while the
                # list is being modified, then rebuild aliases for shifted items.
                removed = [self[index] for index in sorted(indexes, reverse=True)]
                for index in sorted(indexes, reverse=True):
                    self.pop(index)
                self.__element_dict = {
                    alias: position - sum(position > index for index in indexes)
                    for alias, position in self.__element_dict.items()
                    if alias != name and position not in indexes
                }
                return list(reversed(removed))

            @property
            def element(self):
                """Return a new API element wrapper."""
                factory = getattr(sys.modules[self.api_module], f"{self.__element_name}_component")
                return type(factory)(factory.api_function)

        return type('list', (TypedList,), {})


class Component:
    """Add callable assembly and lazy nested properties to a dataclass.

    A generated component instance can be used as a factory first and as a
    populated model afterward. Calling it assigns submitted primitive values,
    invokes the generated behavior hook, stores its result as
    ``operation_result``, and returns the populated instance.
    """
    is_to_dict = False

    def __init__(self, *args, **kwargs):
        """Initialize an API factory instance or the underlying dataclass."""
        logger.debug("initializing class=%s", self.__class__.__name__)
        if len(args):
            self.api_function = args[0]
            self.api_module = self.api_function.__module__
        else:
            super().__init__(**kwargs)

    def __call__(self, **kwargs):
        """Populate and return an API component instance."""
        is_factory = True if len(super().counts) == 1 else False
        instance = type(self)(self.api_function) if is_factory else self
        for attr, value in kwargs.items():
            field = snake_to_camel(attr)
            if is_factory:
                instance.__setattr__(field, value)
            else:
                super().__setattr__(field, value)
        instance.operation_result = instance.api_function(instance, **kwargs)
        return instance

    def __getattribute__(self, name:str)->Any:
        """Resolve schema fields and lazily allocate generated child factories."""
        attribute = snake_to_camel(name)
        if attribute in super().fields:
            if attribute in list(super().__dict__.keys()):
                return super().__getattribute__(attribute)
            api_module = super().__getattribute__('api_module')
            if not Component.is_to_dict and hasattr(sys.modules[api_module], name):
                factory = getattr(sys.modules[api_module], name)
                instance = type(factory)(factory.api_function)
                super().__setattr__(attribute, instance)
                return instance
            return super().__getattribute__(attribute)
        return super().__getattribute__(name)

    def __eq__(self, other):
        return isinstance(other, type(self))

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_dict(self):
        """Return assigned component fields as a wire-ready dictionary.

        Accessing an omitted dataclass field can trigger lazy component
        allocation, so serialization reads the instance dictionary directly
        and includes only fields that were explicitly assigned.
        """
        def serialize(value):
            if isinstance(value, enum.Enum):
                return value.value
            if isinstance(value, list):
                return [serialize(item) for item in value if item is not None]
            if hasattr(value, 'fields'):
                assigned_fields = object.__getattribute__(value, '__dict__')
                return {
                    field_name: serialize(assigned_fields[field_name])
                    for field_name in value.fields
                    if field_name in assigned_fields and assigned_fields[field_name] is not None
                }
            return value
        self_name = self.__class__.__name__[0].lower() + self.__class__.__name__[1:]
        return {self_name: serialize(self)}


class component:
    """Turn a generated dataclass into a callable component factory.

    Applied as ``@component(Model)``, this class receives the generated
    dataclass ``Model`` and then receives the decorated function as the second
    argument to the resulting wrapper. The function is retained by
    :class:`Component` as the component's behavior hook.

    The wrapper first records the dataclass fields on ``base.fields`` so that
    :class:`Component` can distinguish schema properties from ordinary Python
    attributes. It also initializes ``base.counts``, used by ``Component`` to
    distinguish the factory instance from instances it creates.

    Finally, ``__new__`` dynamically creates and returns a class that inherits
    from both ``Component`` and the original dataclass. The returned class has
    the original dataclass fields and initialization behavior, plus callable
    component behavior, deferred nested-component allocation, and ``to_dict``
    serialization supplied by ``Component``. Python replaces the decorated
    function name with an instance of this returned wrapper class.
    """
    def __new__(cls, base):
        """Create the combined ``Component`` and generated-dataclass wrapper.

        Args:
            base: Generated dataclass supplied in ``@component(base)``.

        Returns:
            A dynamic class inheriting from ``Component`` and ``base``. When
            Python applies the decorator to a function, that function becomes
            the behavior hook used by instances of this class.
        """
        base.fields = {f.name:f for f in fields(base)}
        base.counts = []
        return type(f'{base.__name__}', (Component, base,), {})
