import inspect
import enum
import dataclasses
import json
import sys
import os

import importlib
import types

from dataclasses import is_dataclass, fields, _MISSING_TYPE as MISSING_TYPE
from collections import defaultdict
from typing import Any, Union, Optional, List, Dict, Text, ForwardRef, get_type_hints, get_origin, get_args 

# from pepapi import *

import logging
# from utils.xsd_to_py_class import cammel_to_snake
# from dovetail.pepapi import pepapi_import
# from dicts.create_task_response_json import response

logging.basicConfig(format="%(levelname)7s::%(funcName)10s:[%(lineno)3d] - %(message)s")
logging.getLogger().setLevel(logging.DEBUG)

code = defaultdict(lambda:defaultdict(list))
wrap = defaultdict(lambda:defaultdict(list))
stub = defaultdict(lambda:defaultdict(lambda:defaultdict(list)))

wrap_import = defaultdict(set)
api_import = defaultdict(set)
date_import = defaultdict(set)

keys = list()
 
def camel_to_snake(camel:str)->str:
    snake = ''.join(['_'+i.lower() if i.isupper() 
        else i for i in camel]).lstrip('_')
    return snake

def snake_to_camel(snake:str)->str:
    camel = ''.join([(i.capitalize() if n else i) for n, i in enumerate(snake.split('_'))]) 
    return camel
    
#-------------------------------------------------------------------------------
# generate code
#-------------------------------------------------------------------------------
primitives_lists = defaultdict(list)
api_module_name = "pepapi"


def resolved_type_hints(cls):
    """Resolve postponed and forward-referenced annotations for a class."""
    module = sys.modules.get(cls.__module__)
    namespace = vars(module) if module is not None else None
    return get_type_hints(cls, globalns=namespace, localns=namespace)


def is_union_type(annotation):
    """Return whether an annotation is a typing or Python 3.10 union."""
    return get_origin(annotation) in (Union, types.UnionType)


def is_scalar_type(annotation):
    """Return whether an annotation represents a scalar value."""
    try:
        return issubclass(annotation, (str, int, float, bool, bytes))
    except TypeError:
        return annotation in (str, int, float, bool, bytes)


def is_message_envelope(cls):
    """Return whether a root dataclass contains optional operation branches."""
    type_hints = resolved_type_hints(cls)
    return all(
        is_union_type(type_hints[field.name]) and type(None) in get_args(type_hints[field.name])
        for field in fields(cls)
    )


def has_scalar_fields(cls):
    """Return whether a dataclass has scalar or enum fields for a direct factory."""
    for annotation in resolved_type_hints(cls).values():
        annotation_types = [item for item in get_args(annotation) if item is not type(None)]
        if not annotation_types:
            annotation_types = [annotation]
        if all(
            is_scalar_type(item) or (isinstance(item, type) and issubclass(item, enum.Enum))
            for item in annotation_types
        ):
            return True
    return False


def explore(cls:Any, name=None, top=None, depth=0, path=None, access=None, list_type=None, is_list=False, is_optional=False, metadata:Optional[Dict]=None, is_envelope=False)->None:
    """
    explore is being called on top level dataclass e.g. Request or Response and
    recursively on any other dataclass indented into top level dataclass
    """
    #---------------------------------------------------------------------------
    def originate(annotation):
        """
        annotation origin detection closure
        """
        
        nonlocal is_list
        nonlocal is_optional
        
        if origin := get_origin(annotation):
            logging.debug(f"{indent}origin={origin}")
            if origin is list:
                logging.debug(f"{indent}list detected - prev={is_list}")
                is_list = True
            for arg in get_args(annotation):
                logging.debug(f"{indent}processing {arg=}")
                if arg is type(None):
                    logging.debug(f"{indent}optional detected")
                    is_optional = True
                    continue
                return originate(arg)
        else:
            logging.debug(f"{indent}end of origination::{annotation=}")
            return annotation
    #---------------------------------------------------------------------------
    def type_list(top, name, list_type):
        wrap[top][name].append(f"@typedlist({list_type})\ndef {camel_to_snake(name)}(*args):")
        wrap[top][name].append(f'    """\n    {camel_to_snake(name)} list element contains {camel_to_snake(list_type)} elements\n')
        wrap[top][name].append('    there are several ways to add an element to a list:')
        wrap[top][name].append(f'    list_element_ref = {camel_to_snake(name)}({camel_to_snake(list_type)}(...))')
        wrap[top][name].append(f'    {camel_to_snake(name)}.{camel_to_snake(list_type)}_alias(...)')
        wrap[top][name].append('    """\n') 
        wrap[top][name].append('    logger.debug("submitted list element(s): %s", args)')
        wrap_import[top].add(camel_to_snake(name))
    
    #-> generated code and logging indentation based on recursion depth
    indent = ' '*4*depth
    #acme = None
    """
    if depth == 0:
        acme = top # assign the very top level (Request or Response) to current top
    """
    #-> preserve incoming class name (?)
    cls_name = cls.__name__    
    type_hints = resolved_type_hints(cls)
    is_direct_scalar_root = depth == 0 and not is_envelope and has_scalar_fields(cls)
    logging.debug(f"{indent}:>recursion {depth=}:processing class={cls.__name__}:{name=}:{top=}:{path=}:{is_list=}:{is_optional=}")    
    """
    code[top]['init'].append(f"{indent}{(name + ' = ') if depth == 0 else ''}{cls.__name__}(")
    code[top]['json'].append(indent + (name + '={' if depth==0 else '{'))
    logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
    """
    # wrap[top][cls.__name__].append(f"@component({cls.__name__})\ndef {camel_to_snake(cls.__name__)}(\n    {camel_to_snake(cls.__name__)}:{cls.__name__},")
    wrap[top][cls.__name__].append(f"@component({cls.__name__})\ndef {camel_to_snake(name)}(\n    {camel_to_snake(name)}:{cls.__name__},")
    logging.debug(f"Added API entry point:\n@component({cls.__name__})\ndef {camel_to_snake(name)}(\n    {camel_to_snake(name)}:{cls.__name__},")
    
    if depth == 0 and is_envelope: # if processing top request or response envelope class
        # TODO: generalise imports and signature vs. assuming Optional request or response type class
        api_import[top] |= {
            get_args(type_hints[field.name])[0].__name__
            for field in fields(cls)
            if get_args(type_hints[field.name])
        } # add request or response types classes to import
        signature = '    ' + ',\n    '.join([
            f"{camel_to_snake(field.name)}:{get_args(type_hints[field.name])[0].__name__} | None=None"
            for field in fields(cls)
            if get_args(type_hints[field.name])
        ])
        wrap[top][cls.__name__].append(f"{signature}\n):\n    pass")
    elif depth == 0 and not is_direct_scalar_root:
        wrap[top][cls.__name__].append("):\n    pass")
    else:
        code[top]['init'].append(f"{indent}{cls.__name__}(")
        code[top]['json'].append(indent + '{')    
        # acme = top # assign the very top level (Request or Response) to current top
        
    # wrap_import[top].add(camel_to_snake(cls.__name__))
    wrap_import[top].add(camel_to_snake(name))
    logging.debug(f"{top} wraps added import={camel_to_snake(name)}")
    api_import[top].add(cls.__name__)
    logging.debug(f"{top} api added import={cls.__name__}")
    # dataclass init is added via @dataclass wrapper - here we inspect dataclass init signature to go through the class members 
    for _, parameter in inspect.signature(cls).parameters.items():
        logging.debug(f"{indent}init signature::name={parameter.name}, default={parameter.default}, annotation={parameter.annotation}::kind={parameter.kind}")
        
        if depth == 0 and is_envelope:
            keys.append(parameter.name) # use request or response type as a key to separate requests code in code dicts and dump into separate files
            code[parameter.name]['init'].append(f"{indent}{name} = {cls.__name__}(") # prepend per Request or Response type Request or Response class constructor  
            code[parameter.name]['json'].append(f"{indent}{name} = " + '{')          # prepend per Request or Response type request or response dictionary assignment
            top = parameter.name # assign top arg to request or response type when processing Request or Response class
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}") 
        # get annotated class out of parameter signature as well as set is_list and is_optional next recursion args based on parameter annotation
        cls_ = originate(type_hints.get(parameter.name, parameter.annotation))
        logging.debug(f"{indent}{parameter.name=} origin::class={cls_}:{is_list=}:{is_optional=}")
    
        if type(cls_) is ForwardRef:
            logging.debug(f"{indent}processing forward reference {cls_=}::type={type(cls_.__forward_arg__)}::forward_arg={cls_.__forward_arg__}")
            code[top]['init'].append(f'{indent}{parameter.name} = {"[" if is_list else ""}')
            code[top]['json'].append(f'{indent}"{parameter.name}":{"[" if is_list else ""}')
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
            
            if is_list:
                list_type = cls_.__forward_arg__
                type_list(top, parameter.name, list_type)
                
            if cls_ := getattr(sys.modules['pepapi'], cls_.__forward_arg__):
                logging.debug(f"{indent}processing forward reference type class={cls_}")
                path_ext = [camel_to_snake(cls_.__name__)] if depth else []
                access_ext = [camel_to_snake(parameter.name) if is_list else camel_to_snake(cls_.__name__)] #if depth else []
                name_ = cls_.__name__ if is_list else parameter.name
                explore(cls_, name=name_, top=top, depth=depth + 1, list_type=list_type, path=path + path_ext, access=access + access_ext)
                #code[top]['init'].append(f"{indent}{'],' if is_list else ''}")
                #code[top]['json'].append(f"{indent}{'],' if is_list else ''}")
                #logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
            else:
                logging.critical(f"{indent}unknown forward reference...")
            
            code[top]['init'].append(f"{indent}{'],' if is_list else ''}")
            code[top]['json'].append(f"{indent}{'],' if is_list else ''}")
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
        elif type(cls_) is str:
            forward_ref = cls_
            logging.debug(f"{indent}processing string forward reference={forward_ref}")
            code[top]['init'].append(f"{indent}{parameter.name} = {'[' if is_list else ''}")
            code[top]['json'].append(f'{indent}"{parameter.name}":{"[" if is_list else ""}')
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
            
            if is_list:
                list_type = forward_ref
                type_list(top, parameter.name, list_type)
            
            if cls_ := getattr(sys.modules['pepapi'], forward_ref):
                logging.debug(f"{indent}processing forward reference type class={cls_}")
                #logging.debug(f"{indent}processing string forward referece={forward_ref}")
                #code[top]['init'].append(f"{indent}{parameter.name} = {'[' if is_list else ''}")
                #code[top]['json'].append(f'{indent}"{parameter.name}":{"[" if is_list else ""}')
                #logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
                
                path_ext = [camel_to_snake(parameter.name) if is_list else camel_to_snake(cls_.__name__)] if depth else []
                access_ext = [camel_to_snake(parameter.name) if is_list else camel_to_snake(cls_.__name__)] #if depth else []
                name_ = cls_.__name__ if is_list else parameter.name
                explore(cls_, name=name_, top=top, depth=depth + 1, list_type=list_type, path=path + path_ext, access=access + access_ext)
                #code[top]['init'].append(f"{indent}{'],' if is_list else ''}")
                #code[top]['json'].append(f"{indent}{'],' if is_list else ''}")
                #logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
            
                #if is_list:
                #    list_type = forward_ref
                #    type_list(top, parameter.name, list_type)
            else:
                logging.critical(f"{indent}unknown str forward reference...")
            
            code[top]['init'].append(f"{indent}{'],' if is_list else ''}")
            code[top]['json'].append(f"{indent}{'],' if is_list else ''}")
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
        elif (
            not is_scalar_type(cls_)
            and hasattr(sys.modules['pepapi'], cls_.__name__)
            and cls_.__name__ in pepapi_import
        ): # imported from pepapi as * - needs to be addressed
            logging.debug(f"{indent}processing API class={cls_.__name__}")
            code[top]['init'].append(f"{indent}{parameter.name} = {'[' if is_list else ''}")
            code[top]['json'].append(f'{indent}"{parameter.name}":{"[" if is_list else ""}')
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
            
            if is_list:
                list_type = cls_.__name__
                type_list(top, parameter.name, list_type)
            
            path_ext = [camel_to_snake(parameter.name) if is_list else camel_to_snake(cls_.__name__)] if depth  else []
            access_ext = [camel_to_snake(parameter.name) if is_list else camel_to_snake(cls_.__name__)] # if depth  else []
            name_ = cls_.__name__ if is_list else parameter.name
            explore(cls_, name=name_, top=top, depth=depth + 1, list_type=list_type, path=path + path_ext, access=access + access_ext)
            code[top]['init'].append(f"{indent}{']' if is_list else ''}{('#->'+ top +' depth=' + str(depth)) if depth else ('#->' + top + ' out of depth')}")
            code[top]['json'].append(f"{indent}{']' if is_list else ''}{('#->'+ top +' depth=' + str(depth)) if depth else ('#->' + top + ' out of depth')}")            
            logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")
        else:
            logging.debug(f"{indent}processing primitive type={cls_.__name__}")
            if cls_.__name__ not in ('str', 'int', 'float', 'bool', 'bytes', 'datetime', 'date', 'time'):
                api_import[top].add(cls_.__name__)
            
            if cls_.__name__ in ('datetime', 'date', 'time'):
                date_import[top].add(cls_.__name__)
            
            parameter_var = f'{"__".join(path)}{"__" if path else ""}{camel_to_snake(parameter.name)}'
            code[top]['init'].append(f"{indent}{parameter.name} = {parameter_var},")
            code[top]['json'].append(f'{indent}"{parameter.name}": {parameter_var},')
            
            # prepare api methods signatures
            logging.info(f"preparing signature for {parameter.name=}::{parameter.annotation=}::{parameter.default=}")
            type_str = ''
            is_optional = False
            is_union = False
            arg_list = []
            
            parameter_type = type_hints.get(parameter.name, parameter.annotation)
            if is_union_type(parameter_type):
                
                args = get_args(parameter_type)
                
                if type(None) in args:
                    is_optional = True
                    type_str += ''
                if len(args) - is_optional > 1:
                    is_union = True
                    type_str += ''
                
                for arg in args:
                    if arg is type(None):
                        continue
                    arg_list.append(arg.__name__)
                
                type_str += ' | '.join(arg_list) if is_union else ''.join(arg_list)
                if is_optional:
                    type_str += ' | None'
            else:
                type_str += parameter_type.__name__
            
            if parameter.default is not parameter.empty:
                type_str += f'={parameter.default}'               
            
            wrap[top][cls_name].append(f"    {camel_to_snake(parameter.name)}:{type_str},")
            
            if camel_to_snake(parameter.name) not in primitives_lists[cls_name]:
                primitives_lists[cls_name].append(camel_to_snake(parameter.name))
            
            logging.debug(f"{indent}Checking if str has an enum class in union {parameter.name} {parameter.name[0].capitalize() + parameter.name[1:]}")
            parameter_default = None
            if len(arg_list) == 2 and hasattr(sys.modules['pepapi'], arg_list[1]):
                cls__ = getattr(sys.modules['pepapi'], arg_list[1])
                if enum.Enum in cls__.__bases__:
                    api_import[top].add(cls__.__name__)
                    logging.debug(f"{indent}enum class {cls__.__name__} detected - deriving default value")
                    logging.debug(f"{indent}enum={list(cls__)[0].name}:parameter default={parameter.default}")
                    parameter_default = f'"{list(cls__)[0].name}"'
                    logging.debug(f"parameter_default={parameter_default}:parameter.default={parameter.default}:parameter={parameter}") 
                              
            code[top]['args'].append(f"{'__'.join(path)}{'__' if path else ''}{camel_to_snake(parameter.name)} = {parameter_default or (parameter.default if parameter.default is not parameter.empty else (cls_.__name__ + '(1)'))} # {camel_to_snake(parameter.name)}:{parameter.annotation}")
            code[top]['access'].append(f"{parameter.name} = {'.'.join(access)}{'.' if access else ''}{camel_to_snake(parameter.name)} # {parameter.annotation}")
            logging.info(f"args:{name}:{code[top]['args'][-1]} # {path=}")
        
    is_list = False
    is_optional = False
    # Populate each API entry point once after its entire signature is known.
    if not is_scalar_type(cls) and (depth > 0 or is_envelope or is_direct_scalar_root):
        primitives_doc = None
        complex_doc = None

        primitives_list = [
            (
                f"{camel_to_snake(field.name)} = {camel_to_snake(field.name)}_value # "
                f"{'optional' if field.default is None else 'mandatory'}"
            )
            for field in fields(cls)
            if camel_to_snake(field.name) in primitives_lists[cls_name]
        ]

        if primitives_list:
            primitives_doc = (
                f"    the element is populated as:\n    {camel_to_snake(cls_name)}(\n        "
                + '\n        '.join(primitives_list)
                + '\n    )'
            )

        complex_list = [
            f"{camel_to_snake(cls_name)}.{camel_to_snake(field.name)} # optional"
            for field in fields(cls)
            if camel_to_snake(field.name) not in primitives_lists[cls_name]
        ]

        if complex_list:
            complex_doc = "\n    the element nested element(s) are added as:\n    " + '\n    '.join(complex_list) + '\n'

        return_doc = (
            f"    the element population operation returns a reference to the {camel_to_snake(cls_name)} element instance\n"
            "    the element nested element addition operation returns a reference to added element"
        )

        wrap[top][cls_name].append('):\n    """')
        if primitives_doc:
            wrap[top][cls_name].append(primitives_doc)
        if complex_doc:
            wrap[top][cls_name].append(complex_doc)
        wrap[top][cls_name].append(return_doc)
        wrap[top][cls_name].append('    """\n')
        if primitives_doc:
            params_log = "logger.debug('submitted parameters: " + ','.join([f'{param}=%s' for param in primitives_lists[cls_name]]) + "',\n    " + ', '.join(primitives_lists[cls_name]) + ")"
            wrap[top][cls_name].append(f"\n    {params_log}")
            element_log = "logger.debug('committed message properties: " + ', '.join([f'{param}=%s' for param in primitives_lists[cls_name]]) + "',\n    " + ', '.join([f'{camel_to_snake(cls_name)}.{param}' for param in primitives_lists[cls_name]]) + ")"
            wrap[top][cls_name].append(f"\n    {element_log}")
        else:
            wrap[top][cls_name].append("\n    pass")

    list_type = None
    # end of for cls signature investigation          
    logging.debug(f"{indent}:<recursion {depth=}:processing class={cls.__name__}:{name=}:{top=}:{path=}:{is_list=}:{is_optional=}")  
    code[top]['init'].append(f"{indent}){', #' if depth else ''}")
    code[top]['json'].append(f"{indent}{'' if is_list else ''}" + "}" + (", #" if depth else ""))
    
    if depth == 1:
        code[top]['init'].append(")")
        code[top]['json'].append("}")
    elif depth == 0:
        del code[top]['init'][-1]
        del code[top]['json'][-1]
    
    logging.info(f"\ninit:{code[top]['init'][-1]}\njson:{code[top]['json'][-1]}")    


def invert(structure, field_name=None, path=None, chain=None, params=None, stubs=None, accessors=None, is_list=False, list_depth=0, depth=0):
    """
    start with top level request or response object and recusively flatten out indented objects and lists of objects
    so that immediate attributes are assigned first, then encapsulated objects in the same manner and then
    lists of objects. The purpose is to simplify request or response forming and break up indented initializations
    into more manageable blocks
    e.g.:
    request = some_request(foo=bar, some_object=some_object(bar=foo), other_objects=[other_object(a=42),...])
    becomes:
    request = some_request(foo=bar)
    request.some_object(bar=foo)
    list_of_other_objects = request.other_objects
    elem_other_object_1 = other_object(a=42)
    elem_other_object_2 = other_object(c=22)
    list_of_other_objects(elem_other_object_1, elem_other_object_2)
    """
    
    logging.debug(f"entering::class={structure.__class__.__name__}:{field_name=}:{path=}")
    
    if is_dataclass(structure):
        type_hints = resolved_type_hints(structure.__class__)
        
        primitives = list()  # list of dataclass primitives (non-lists, non-dataclasses)
        dataclasses = list() # list dataclasses to process after primitives
        lists = list()       # list of lists to process after dataclasses
        
        # separate current iteration dataclass object primitives, indented dataclasses, and lists fields into respective lists
        # to process separately in this particular order
        for field in fields(structure):
            attr = getattr(structure, field.name)
            if is_dataclass(attr):
                dataclasses.append(field)
            elif isinstance(attr, list):
                lists.append(field)
            else:
                primitives.append(field)

        # current element name is list element snaked type name if the element is a list member or 
        # passed field name argument if not None (non-zero depth) or 
        # snaked element class name (effectively the entry request or response class name) stripped to request or response token
        elem_name = camel_to_snake(structure.__class__.__name__ if is_list else (field_name or structure.__class__.__name__))
        
        # chop of request string from whatever request type it might be
        if depth: # inside of the messsage structure
            message_type = None # message type only needed at the initial entry into request or response object
        else: # initial entry
            message_type = elem_name # on initial entry top element is message type e.g. optimization request
            # leave only request or response part from request or response message type
            elem_name = elem_name.split('_')[-1]
        
        # on initial entry (if no depth path is set just yet) left hand expression is message type object shortened to last part
        # otherwise if the element is part of the list then it is to be initialized outside of the path depth and then added to a list 
        # finally is there were no lists in the path then no intermediate variable is needed
        # e.g.: request = some_request(foo=bar, list_of_obejcts = [object(bar=foo)])
        # 1. get the list first - tmp_list = request.list_of_objects (note that tmp_list is a ref to request.list_of_objects)
        # 2. elem_object = object(bar=foo) has to be intialized seoarately unlike how foo could be initialised as request.foo = bar
        # 3. tmp_list(elem_object) - adds elem_object to request.list_of_objects
        lh_expr = (f'elem__{elem_name} = ' if is_list else '') if path else f'{elem_name} = '
        # right hand expression is effectively a suggested best effort shortest unique variavle name to reflect variable place
        # in the strucutre
        # TODO - verify full path vs. last path element
        # rh_expr = ((path[-1] + '.') if path and not is_list else '') + (message_type or elem_name)
        rh_expr = (('.'.join(path) + '.') if path and not is_list else '') + (message_type or elem_name)
        logging.debug(f"{' '*4*(depth)}{depth=}:incoming {field_name=}:current {elem_name=}:{message_type=}:{is_list=}:{path=}:{chain=}:{list_depth=}:")
        logging.debug(f"{' '*4*(depth)}{lh_expr}{rh_expr}(")
        
        stubs.append(f"{lh_expr}{rh_expr}(")
        # process primitives arguments 
        params_ = list()
        accessors_ = list()
        
        for field in primitives:
            logging.debug(f"{' '*4*depth}{depth=}:processing primitives::primitive={field.name}:{elem_name=}:{is_list=}:{path=}:{chain=}:{field}")
            
            field_type = type_hints.get(field.name, field.type)
            if is_union_type(field_type):
                args = get_args(field_type)
                enumeral = [
                    arg for arg in args
                    if isinstance(arg, type) and issubclass(arg, enum.Enum)
                ]
                if enumeral:
                    default = f'"{list(enumeral[-1])[0].name}"'
                elif field.default is MISSING_TYPE:
                    default = f"{args[0].__name__}(1)"
                else:
                    default = field.default
            else:
                    default = f"{field_type.__name__}(1)"
            
            lh_expr = camel_to_snake(field.name)
            path_idx = 2 if is_list else 1 # last item in the path is list name if the element is part of a list yet we need an element
            # right hand expression: previous element name and this element name and variable name or element name and variable name if depth is 1 or just variable name if depth is 0 
            rh_expr = ((path[-path_idx] + '__' + elem_name + '__') if len(path) >=path_idx and path[-path_idx] != path[0] else ((elem_name + '__') if path else '')) + camel_to_snake(field.name)
            params_.append(f"    {lh_expr} = {rh_expr}")
            params.append(f"{rh_expr} = {default}")
            accessor = f'{rh_expr} = {".".join(chain) if chain else elem_name}{"" if is_list else (("." + field_name) if field_name else "")}.{camel_to_snake(field.name)} # {depth=}::{field_name=}::{elem_name=}::{is_list=}::{chain=}'
            accessors_.append(accessor)
            accessors.append(accessor)
        
        logging.debug(',\n    ' + ',\n    '.join(params_))
        logging.debug(',\n    ' + ',\n    '.join(accessors_))
        stubs.append(',\n'.join(params_))
        logging.debug(f"{' '*4*depth})")
        stubs.append(")")

        # now we take case of dataclasses and lists in that order
        for field in dataclasses:
            logging.debug(f"{' '*4*depth}{depth=}:processing dataclasses::class={field.name}:{is_list=}:{chain=}:{elem_name}:{path=}")
            invert(
                getattr(structure, field.name),
                field_name=camel_to_snake(field.name),
                #path=path + [elem_name],
                path = [f'elem__{elem_name}'] if is_list else (path + [elem_name]),
                list_depth=list_depth,
                depth=depth + 1,
                chain=chain + ([] if is_list else [elem_name]),
                params=params,
                stubs=stubs,
                accessors=accessors
            )
        
        for field in lists:
            logging.debug(f"{' '*4*depth}{depth=}:processing lists::list={field.name}:{chain=}:{elem_name}")
            invert(
                getattr(structure, field.name),
                field_name=camel_to_snake(field.name),
                path=path + [elem_name],
                list_depth=list_depth,
                depth=depth + 1,
                # chain=chain + [] if depth else [elem_name],
                chain=chain + ([] if is_list else [elem_name]) if depth else [elem_name],
                params=params,
                stubs=stubs,
                accessors=accessors
            )
        
        return elem_name
    
    elif isinstance(structure, list):
        # previous element in path if we're already in a list or full path if list(s) were not entered yet  
        elem_name = 'elem__' + path[-1] if list_depth else '.'.join(path)
        logging.debug(f"{' '*4*depth}list__{field_name} = {elem_name}.{field_name} #---> {path=}:{field_name=}:{is_list=}:{list_depth=}")
        stubs.append(f'# allocating {elem_name} property {field_name} list')
        stubs.append(f"list__{field_name} = {elem_name}.{field_name}")
        for element in structure:
            logging.debug(f"{' '*4*depth}{depth=}:processing list elements::{element=}:{is_list=}:{list_depth=}:{chain=}:{path=}")
            list_element = invert(
                element, 
                field_name=field_name,
                path=path + [field_name],
                is_list=True,
                list_depth=list_depth+1,
                depth=depth+1,
                chain=chain + [f"{field_name}[0]"],
                params=params,
                stubs=stubs,
                accessors=accessors
            )
            logging.debug(f"{' '*4*depth}list__{field_name}(elem__{list_element}) #---> {path}:{elem_name=}{field_name=}:{is_list=}:{list_depth=}:{depth=}")
            stubs.append(f'# adding {list_element} element to {field_name} list')
            stubs.append(f"list__{field_name}(elem__{list_element})\n")
    else:
        pass

#===============================================================================
# process command line arguments 
#===============================================================================
def parse_args():
    import argparse
    
    this_dir = os.path.dirname(__file__)    
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--api_name", type=str, default="pepapi", help="api name - will be used to create and populate api modules directory")
    parser.add_argument("--tmp_api_lib", type=str, default=os.path.join(this_dir, os.path.pardir, os.path.pardir, '_dovetail'), help="tmp api lib - will be used to create and populate tmp api modules directory")
    parser.add_argument("--api_lib", type=str, default=os.path.join(this_dir, os.path.pardir), help="api lib - will be used to create and populate api modules directory")
    parser.add_argument("--inits_dir", type=str, default=os.path.join(this_dir, os.path.pardir, 'inits'), help="inits directory - will be used to populate with init stubs")
    parser.add_argument("--dicts_dir", type=str, default=os.path.join(this_dir, os.path.pardir, 'dicts'), help="dicts directory - will be used to populate with dict (json) stubs")
    parser.add_argument("--stubs_dir", type=str, default=os.path.join(this_dir, os.path.pardir, 'stubs'), help="api code stubs directory - will be used to populate with test code stubs")
    parser.add_argument("--request_class", type=str, default="Request", help="python class name for schema request sequence")
    parser.add_argument("--response_class", type=str, default="", help="optional Python class name for a response sequence")
    parser.add_argument("--logging_level", type=str, default="DEBUG", help="logging level")
    parser.add_argument("--write_to_file", action='store_true', help="write generated code to files")
    args = parser.parse_args()
    return args       
#===============================================================================
# process request and response 
#===============================================================================            
banner_len = 110

def gen_init_and_json_code(cls):
    
    #for cls in (Request, Response):
    Name = cls.__name__
        
    name = camel_to_snake(Name)
    banner_pad = (banner_len - len(name) - 1) // 2
    
    print(f"#{'='*banner_len}")
    print(f"#{'='*banner_pad} {name} {'='*banner_pad}")
    print(f"#{'='*banner_len}")
        
    explore(
        cls,
        name=name,
        top=Name,
        path=list(),
        access=list(),
        is_envelope=is_message_envelope(cls),
    )

#===============================================================================
# class bulk instantiation
#===============================================================================
write_to_file=False

def write_init_code(write_dir_path="../inits", is_write_to_file=False):
    
    for key in keys:
        message_type = 'request' if 'request' in key.lower() else 'response'
        if is_write_to_file:
            stdout = sys.stdout
            file = open(f"{write_dir_path}/{camel_to_snake(key)}_init.py", "w")
            sys.stdout = file
        
        print("from pepapi import *\n")
        
        banner_pad = (banner_len - len(key) - 1) // 2
        
        print(f"#{'='*banner_len}")
        print(f"#{' '*banner_pad} {key} {' '*banner_pad}")
        print(f"#{'='*banner_len}")
        
        print('\n')
    
        for line in code[key]['args']:
            print(line)
        
        print('\n')
        
        for line in code[key]['init']:
            print(line)
            
        print('if __name__ == "__main__":')
        print("    import dacite")
        print("    from dataclasses import asdict\n")
        
        print(f"    test_{message_type} = dacite.from_dict({message_type.capitalize()}, asdict({message_type}))")
        print(f"    assert({message_type} == test_{message_type})")
    
        if is_write_to_file:
            file.close()
            sys.stdout = stdout

#===============================================================================
# json representation
#===============================================================================
def write_json_code(write_dir_path="../dicts", is_write_to_file=False):
    
    for key in keys: 
        message_type = 'request' if 'request' in key.lower() else 'response'
        if is_write_to_file:
            stdout = sys.stdout
            file = open(f"{write_dir_path}/{camel_to_snake(key)}_dict.py", "w")
            sys.stdout = file
            
        print("from pepapi import *\n")
        print('\n')
        
        banner_pad = (banner_len - len(key) - 1) // 2
           
        print(f"#{'='*banner_len}")
        print(f"#{' '*banner_pad} {key} {' '*banner_pad}")
        print(f"#{'='*banner_len}")
        
        print('\n')
    
        for line in code[key]['args']:
            print(line)
        
        print('\n')
                
        for line in code[key]['json']:
            print(line)
        
        print('if __name__ == "__main__":')
        print("    import dacite")
        print("    from dataclasses import asdict\n")
    
        print(f"    test_{message_type} = dacite.from_dict({message_type.capitalize()}, {message_type})")
        print(f"    dict_{message_type} = " + "{" + f"key:val for key, val in asdict(test_{message_type}).items() if val is not None" + "}")
        print(f"    assert({message_type} == dict_{message_type})")
        
        if is_write_to_file:
            file.close()
            sys.stdout = stdout

#===============================================================================
# api entry points
#===============================================================================
def write_api_entry_points(write_dir_path="../../_dovetail", is_write_to_file=False):
    
    for key in wrap:
        if is_write_to_file:
            stdout = sys.stdout
            file = open(f"{write_dir_path}/{camel_to_snake(key)}.py", "w")
            sys.stdout = file
        
        banner_pad = (banner_len - len(key) - 1) // 2
        
        print('from __future__ import annotations')
        print('import logging')
        print('logger = logging.getLogger(__name__)')
        if len(date_import[key]):
            print(f'from datetime import {", ".join(list(date_import[key]))}')
        print(f'from {api_module_name} import {", ".join(list(api_import[key]))}')
        print('from pylib.decorators import typedlist, component')
        print()
        
        multiple_classes = dict()
           
        for cls in wrap[key]:
            banner_pad = (banner_len - len(cls) - 1) // 2
            print(f"#{'-'*banner_len}")
            print(f"#{' '*banner_pad} {key}:{cls} {' '*banner_pad}")
            print(f"#{'-'*banner_len}")
            is_multiple = False
            for line_num, line in enumerate(wrap[key][cls]):
                if line_num == 0:
                    multiple_classes[line] = 0
                elif line in multiple_classes:
                    logging.warning(f"# repetitive class={cls}")
                    multiple_classes[line] += 1
                    is_multiple = True    
                if not is_multiple:
                    print(line)  
            if is_multiple:
                logging.debug("# there were multiple classes detected")
            else:
                logging.debug("# single class")
        
        if is_write_to_file:
            file.close()
            sys.stdout = stdout
        
#===============================================================================
# stubs
#===============================================================================

def write_code_stubs(write_dir_path="../stubs", is_write_to_file=False):
    from inspect import getmembers, isfunction, isclass
    from os import linesep
    
    params = defaultdict(list)
    stubs = defaultdict(list)
    accessors = defaultdict(list)
    
    for key in keys:
        message_type = 'request' if 'request' in key.lower() else 'response'
        
        if is_write_to_file:
            stdout = sys.stdout
            file = open(f"{write_dir_path}/{camel_to_snake(key)}_stub.py", "w")
            sys.stdout = file
    
        logging.debug(f"processing {key=}:{camel_to_snake(key)}_init.py")
        module = importlib.import_module(f"{camel_to_snake(key)}_init")
        name = camel_to_snake(key).split('_')[-1]
        obj = getattr(module, name)
        structure = getattr(obj, key)
        logging.debug(f"generating stub for {file=}:{name=}:{key=}...")
        banner_pad = (banner_len - len(key) - 1) // 2
        
        print('"""')
        print(f'The following is {camel_to_snake(key)} {message_type} forming code stub')
        print(f'The stub example demonstrates indented {message_type} sequential assembly')
        print('via first initializing request components with primitives properties')
        print('and later assigning complex (other nested components and lists) properties once they are also intialized')
        print('"""')
        print()
        print('import logging')
        print('logger = logging.getLogger(__name__)')
        print(f'from {camel_to_snake(key)} import {", ".join(list(wrap_import[key]))}')
        print()
        
        invert(structure, path=[], chain=[], params=params[key], stubs=stubs[key], accessors=accessors[key])
        print()
        print('# the following arguments naming convention is not requered and rather provided to signify argument place')
        print(f'# in {message_type} structure')
        print('# provided values are strictly indicative of type (hence are type conversions) or set to first (not default) enum string value if such expected')
        print()
        print(linesep.join(params[key]))
        print()
        print('# the following are message forming steps facilitating de-encapsulation of by design indented message object structure')
        print()
        print(linesep.join(stubs[key]))
        print()
        print('# the following are message elements access path (accessors) stubs')
        print()
        print(linesep.join(accessors[key]))
        
        if is_write_to_file:
            file.close()
            sys.stdout = stdout
        
if __name__ == "__main__":
    
    args = parse_args()
    
    logging.basicConfig(format="%(levelname)7s::%(name)s:%(funcName)10s:[%(lineno)3d] - %(message)s")
    logging.getLogger().setLevel(args.logging_level)    
    
    sys.path.append(args.inits_dir)
    sys.path.append(args.dicts_dir)
    sys.path.append(args.api_lib)
    
    api_lib = importlib.import_module(args.api_name)
    api_module_name = args.api_name
    sys.modules['pepapi'] = api_lib
    
    request_class = getattr(api_lib, args.request_class)
    response_class = getattr(api_lib, args.response_class) if args.response_class else None
    pepapi_import = getattr(
        api_lib,
        args.api_name + "_import",
        getattr(api_lib, "pepapi_import", []),
    )
    
    logging.info(f"{args.inits_dir=}:{args.dicts_dir=}:{args.stubs_dir=}:{args.api_lib=}")
    logging.info("keys=%s", keys)
    
    gen_init_and_json_code(request_class)
    if response_class is not None:
        gen_init_and_json_code(response_class)
    write_init_code(write_dir_path=args.inits_dir, is_write_to_file=args.write_to_file)
    write_json_code(write_dir_path=args.dicts_dir, is_write_to_file=args.write_to_file)
    write_api_entry_points(write_dir_path=args.tmp_api_lib, is_write_to_file=args.write_to_file)
    write_code_stubs(write_dir_path=args.stubs_dir, is_write_to_file=args.write_to_file)
    