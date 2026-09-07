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
    """list with list element type checking wrapper factory"""
    def __new__(self, cls):
        """generate typed list class instance"""
        logger.debug("generating %s typed list class instance", cls.__name__)
        class TypedList(list):
            """typed list class extension"""
            def __init__(self, arg:Union[Callable, Generator]):
                """Initialize an API wrapper or a list from a generator."""
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
                for val in args:
                    replacement = replace(val)
                    self.append(replacement)
                self.api_function(args)
                return self

            def __getattr__(self, name):
                logger.debug("requesting name=%s", name)
                if name in self.__element_dict:
                    return self[self.__element_dict[name]]
                factory = getattr(sys.modules[self.api_module], self.__element_name)
                instance = type(factory)(factory.api_function)
                self.append(instance)
                self.__element_dict[name] = len(self) - 1
                return instance

            def append(self, element):
                if not isinstance(element, self.__element_type):
                    msg = f'Expected list member type={self.__element_type.__name__}::received list member type={type(element).__name__}'
                    logger.critical(msg)
                    raise TypeError(msg)
                list.append(self, element)

            @property
            def element(self):
                """Return a new API element wrapper."""
                factory = getattr(sys.modules[self.api_module], self.__element_name)
                return type(factory)(factory.api_function)

        return type('list', (TypedList,), {})


class Component:
    """Base class adding callable API behavior to generated dataclasses."""
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
        instance.evaluation_result = instance.api_function(instance, **kwargs)
        return instance

    def __getattribute__(self, name:str)->Any:
        """Resolve API field access using the generated API module."""
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
        """Return this API component as a dictionary without None values."""
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
