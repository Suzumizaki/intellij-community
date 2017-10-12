from _pydev_bundle import pydev_log
import traceback
from _pydevd_bundle import pydevd_extension_utils
from _pydevd_bundle import pydevd_resolver
import sys
from _pydevd_bundle.pydevd_constants import dict_iter_items, dict_keys, IS_PY3K, \
    IS_PY2, BUILTINS_MODULE_NAME, MAXIMUM_VARIABLE_REPRESENTATION_SIZE, RETURN_VALUES_DICT, LOAD_VALUES_ASYNC, \
    DEFAULT_VALUE

from _pydev_bundle.pydev_imports import quote
from _pydevd_bundle.pydevd_extension_api import TypeResolveProvider, StrPresentationProvider
try:
    import types
    frame_type = types.FrameType
except:
    frame_type = None

try:
    from xml.sax.saxutils import escape

    def make_valid_xml_value(s):
        return escape(s, {'"': '&quot;'})
except:
    #Simple replacement if it's not there.
    def make_valid_xml_value(s):
        return s.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

class ExceptionOnEvaluate:
    def __init__(self, result):
        self.result = result


_IS_JYTHON = sys.platform.startswith("java")
if not _IS_JYTHON:
    _default_type_map = [
        # None means that it should not be treated as a compound variable

        # isintance does not accept a tuple on some versions of python, so, we must declare it expanded
        (type(None), None,),
        (int, None),
        (float, None),
        (complex, None),
        (str, None),
        (tuple, pydevd_resolver.tupleResolver),
        (list, pydevd_resolver.tupleResolver),
        (dict, pydevd_resolver.dictResolver),
    ]
    try:
        _default_type_map.append((long, None))  # @UndefinedVariable
    except:
        pass  # not available on all python versions

    try:
        _default_type_map.append((unicode, None))  # @UndefinedVariable
    except:
        pass  # not available on all python versions

    try:
        _default_type_map.append((set, pydevd_resolver.setResolver))
    except:
        pass  # not available on all python versions

    try:
        _default_type_map.append((frozenset, pydevd_resolver.setResolver))
    except:
        pass  # not available on all python versions

    try:
        from django.utils.datastructures import MultiValueDict

        _default_type_map.insert(0, (MultiValueDict, pydevd_resolver.multiValueDictResolver))
        # we should put it before dict
    except:
        pass  # django may not be installed

    try:
        from django.forms import BaseForm

        _default_type_map.insert(0, (BaseForm, pydevd_resolver.djangoFormResolver))
        # we should put it before instance resolver
    except:
        pass  # django may not be installed

    try:
        from collections import deque

        _default_type_map.append((deque, pydevd_resolver.dequeResolver))
    except:
        pass

    if frame_type is not None:
        _default_type_map.append((frame_type, pydevd_resolver.frameResolver))

else:
    from org.python import core  # @UnresolvedImport

    _default_type_map = [
        (core.PyNone, None),
        (core.PyInteger, None),
        (core.PyLong, None),
        (core.PyFloat, None),
        (core.PyComplex, None),
        (core.PyString, None),
        (core.PyTuple, pydevd_resolver.tupleResolver),
        (core.PyList, pydevd_resolver.tupleResolver),
        (core.PyDictionary, pydevd_resolver.dictResolver),
        (core.PyStringMap, pydevd_resolver.dictResolver),
    ]
    if hasattr(core, 'PyJavaInstance'):
        # Jython 2.5b3 removed it.
        _default_type_map.append((core.PyJavaInstance, pydevd_resolver.instanceResolver))


class TypeResolveHandler(object):
    __instance = None

    NO_PROVIDER = []  # Sentinel value (any mutable object to be used as a constant would be valid).

    def __init__(self):
        self.default_type_map = _default_type_map
        self.resolve_providers = pydevd_extension_utils.extensions_of_type(TypeResolveProvider)
        self.str_providers = pydevd_extension_utils.extensions_of_type(StrPresentationProvider)

        # Note: don't initialize with the types we already know about so that the extensions can override
        # the default resolvers that are already available if they want.
        self._type_to_resolver_cache = {}
        self._type_to_str_provider_cache = {}

    def get_type(self, o):
        try:
            try:
                # Faster than type(o) as we don't need the function call.
                type_object = o.__class__
            except:
                # Not all objects have __class__ (i.e.: there are bad bindings around).
                type_object = type(o)

            type_name = type_object.__name__
        except:
            # This happens for org.python.core.InitModule
            return 'Unable to get Type', 'Unable to get Type', None

        return self._get_type(o, type_object, type_name)

    def _get_type(self, o, type_object, type_name):
        resolver = self._type_to_resolver_cache.get(type_object)
        if resolver is not None:
            return type_object, type_name, resolver

        try:
            for resolver in self.resolve_providers:
                if resolver.can_provide(type_object, type_name):
                    # Cache it
                    self._type_to_resolver_cache[type_object] = resolver
                    return type_object, type_name, resolver

            for t in self.default_type_map:
                if isinstance(o, t[0]):
                    # Cache it
                    resolver = t[1]
                    self._type_to_resolver_cache[type_object] = resolver
                    return (type_object, type_name, resolver)
        except:
            traceback.print_exc()

        # No match return default (and cache it).
        resolver = pydevd_resolver.defaultResolver
        self._type_to_resolver_cache[type_object] = resolver
        return type_object, type_name, resolver

    if _IS_JYTHON:
        _base_get_type = _get_type

        def _get_type(self, o, type_object, type_name):
            if type_name == 'org.python.core.PyJavaInstance':
                return type_object, type_name, pydevd_resolver.instanceResolver

            if type_name == 'org.python.core.PyArray':
                return type_object, type_name, pydevd_resolver.jyArrayResolver

            return self._base_get_type(o, type_name, type_name)

    def str_from_providers(self, o, type_object, type_name):
        provider = self._type_to_str_provider_cache.get(type_object)

        if provider is self.NO_PROVIDER:
            return None

        if provider is not None:
            return provider

        for provider in self.str_providers:
            if provider.can_provide(type_object, type_name):
                self._type_to_str_provider_cache[type_object] = provider
                return provider.get_str(o)

        self._type_to_str_provider_cache[type_object] = self.NO_PROVIDER
        return None


_TYPE_RESOLVE_HANDLER = TypeResolveHandler()

""" 
def get_type(o):
    Receives object and returns a triple (typeObject, typeString, resolver).

    resolver != None means that variable is a container, and should be displayed as a hierarchy.

    Use the resolver to get its attributes.

    All container objects should have a resolver.
"""
get_type = _TYPE_RESOLVE_HANDLER.get_type

_str_from_providers = _TYPE_RESOLVE_HANDLER.str_from_providers


def is_builtin(x):
    return getattr(x, '__module__', None) == BUILTINS_MODULE_NAME


def should_evaluate_full_value(val):
    return not LOAD_VALUES_ASYNC or (is_builtin(type(val)) and not isinstance(val, (list, tuple, dict)))


def return_values_from_dict_to_xml(return_dict, eval_full_val=True):
    res = ""
    for name, val in dict_iter_items(return_dict):
        res += var_to_xml(val, name, additionalInXml=' isRetVal="True"', evaluate_full_value=eval_full_val)
    return res


def frame_vars_to_xml(frame_f_locals, hidden_ns=None, dbg=None, thread_id=None, frame_id=None):
    """ dumps frame variables to XML
    <var name="var_name" scope="local" type="type" value="value"/>
    """
    xml = ""

    keys = dict_keys(frame_f_locals)
    if hasattr(keys, 'sort'):
        keys.sort() #Python 3.0 does not have it
    else:
        keys = sorted(keys) #Jython 2.1 does not have it

    for k in keys:
        try:
            v = frame_f_locals[k]
            eval_full_val = should_evaluate_full_value(v)

            if k == RETURN_VALUES_DICT:
                xml += return_values_from_dict_to_xml(v, eval_full_val=eval_full_val)
            else:
                if hidden_ns is not None and k in hidden_ns:
                    xml += var_to_xml(v, str(k), additionalInXml=' isIPythonHidden="True"', evaluate_full_value=eval_full_val)
                else:
                    xml += var_to_xml(v, str(k), evaluate_full_value=eval_full_val)
        except Exception:
            traceback.print_exc()
            pydev_log.error("Unexpected error, recovered safely.\n")

    return xml


def var_to_xml(val, name, doTrim=True, additionalInXml='', evaluate_full_value=True):
    """ single variable or dictionary to xml representation """

    is_exception_on_eval = isinstance(val, ExceptionOnEvaluate)

    if is_exception_on_eval:
        v = val.result
    else:
        v = val

    _type, typeName, resolver = get_type(v)
    type_qualifier = getattr(_type, "__module__", "")

    if not evaluate_full_value:
        value = DEFAULT_VALUE
    else:
        try:
            str_from_provider = TypeResolveHandler.instance().str_from_providers(v, _type, typeName)
            if str_from_provider is not None:
                value = str_from_provider
            elif hasattr(v, '__class__'):
                if v.__class__ == frame_type:
                    value = pydevd_resolver.frameResolver.get_frame_name(v)

                elif v.__class__ in (list, tuple, dict):
                    if len(v) > 300:
                        value = '%s: %s' % (str(v.__class__), '<Too big to print. Len: %s>' % (len(v),))
                    else:
                        value = '%s: %s' % (str(v.__class__), v)
                else:
                    try:
                        cName = str(v.__class__)
                        if cName.find('.') != -1:
                            cName = cName.split('.')[-1]

                        elif cName.find("'") != -1: #does not have '.' (could be something like <type 'int'>)
                            cName = cName[cName.index("'") + 1:]

                        if cName.endswith("'>"):
                            cName = cName[:-2]
                    except:
                        cName = str(v.__class__)

                    if resolver is not None and getattr(resolver,'use_value_repr_instead_of_str', False):
                        value = '%s: %r' % (cName, v)
                    else:
                        value = '%s: %s' % (cName, v)
            else:
                value = str(v)
        except:
            try:
                value = repr(v)
            except:
                value = 'Unable to get repr for %s' % v.__class__

    try:
        name = quote(name, '/>_= ') #TODO: Fix PY-5834 without using quote
    except:
        pass

    xml = '<var name="%s" type="%s" ' % (make_valid_xml_value(name), make_valid_xml_value(typeName))

    if type_qualifier:
        xmlQualifier = 'qualifier="%s"' % make_valid_xml_value(type_qualifier)
    else:
        xmlQualifier = ''

    if value:
        #cannot be too big... communication may not handle it.
        if len(value) > MAXIMUM_VARIABLE_REPRESENTATION_SIZE and doTrim:
            value = value[0:MAXIMUM_VARIABLE_REPRESENTATION_SIZE]
            value += '...'

        #fix to work with unicode values
        try:
            if not IS_PY3K:
                if isinstance(value, unicode):
                    value = value.encode('utf-8')
            else:
                if isinstance(value, bytes):
                    value = value.encode('utf-8')
        except TypeError: #in java, unicode is a function
            pass

        xmlValue = ' value="%s"' % (make_valid_xml_value(quote(value, '/>_= ')))
    else:
        xmlValue = ''

    if is_exception_on_eval:
        xmlCont = ' isErrorOnEval="True"'
    else:
        if resolver is not None:
            xmlCont = ' isContainer="True"'
        else:
            xmlCont = ''

    return ''.join((xml, xmlQualifier, xmlValue, xmlCont, additionalInXml, ' />\n'))

