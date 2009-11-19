import sys

import yaml

try:
    import simplejson
except ImportError:
    import json

from babbisch.tag import translate, parse_string
from babbisch.odict import odict

from .wraplib.codegen import Codegen
from .wraplib.ooc import Cover, Method, Function, Attribute, Class

from .types import TYPE_MAP
from .names import oocize_name, oocize_type

class WTFError(Exception):
    pass

class NamingImpossibleError(Exception):
    pass

class OOClient(object):
    def __init__(self, objects, interface):
        #: odict of babbisch objects.
        self.objects = objects
        #: Dictionary containing the user-defined YAML interface.
        self.interface = interface
        #: odict {name: codegen} of *all* codegens.
        self.codegens = odict()
        # fill in all primitive types
        self.create_primitives()

    def create_primitives(self):
        """
            update `self.objects`; add primitive types from TYPE_MAP.
        """
        for tag, ooc_name in TYPE_MAP.iteritems():
            self.objects[tag] = {
                                'class': 'Primitive',
                                'tag': tag,
                                'name': ooc_name,
                                'ooc_name': ooc_name,
                                'c_name': tag,
                                'wrapped': True,
                                }

    def add_wrapper(self, obj, wrapper):
        """
            Set *obj* the wrapper codegen of *wrapper*.
            Do two things:
             1) set ``obj['wrapper'] = wrapper``
             2) append *wrapper* to `self.codegens`
             3) set ``obj['wrapped'] = True``
        """
        obj['wrapper'] = self.codegens[wrapper.name] = wrapper
        obj['wrapped'] = True

    def get_wrapper(self, tag):
        """
            Get the wrapper of the object identified by the tag *tag*.
        """
        return self.objects[tag]['wrapper']

    def is_wrapped(self, tag):
        """
            Return a boolean value that describes whether the object with
            the tag *tag* is wrapped or not.
        """
        return self.objects[tag].get('wrapped', False)

    def run(self):
        """
            Run the binding generator.

            Generating object oriented bindings is done in these steps:

             1) Create ooc names for all objects (:meth:`create_ooc_names`)
             2) Create C names for all objects (:meth:`create_c_name`)
             3) Generate code for types (structs, unions, enums, typedefs)
             4) Generate code for functions
             5) Generate aaaaallllll code and return it as string.

        """
        self.create_ooc_names()
        self.create_c_names()
        self.generate_types()
        self.generate_functions()
        return self.generate_code()

    def generate_code(self):
        """
            Return the generated code as string.
        """
        return Codegen()(self.codegens.values()).buf

    def get_ooc_type(self, tag):
        """
            get the ooc type from the tag *tag*. It might be nested.
            And might be a pointer. Or an array. Whatever! It can
            be *anything*!
        """
        if tag in self.objects:
            return self.objects[tag]['ooc_name']
        else:
            if '(' in tag:
                mod, args = parse_string(tag)
                
                def _pointer():
                    return self.get_ooc_type(translate(args[0])) + '*'

                def _const():
                    return 'const %s' % self.get_ooc_type(translate(args[0]))

                return {
                    'POINTER': _pointer,
                    'CONST': _const,
                }[mod]()
            else:
                raise WTFError('WTF tag is this? %r' % tag)

    def generate_ooc_name(self, obj):
        """
            Return an appropriate ooc name for the object *obj*.

            Structs
                oocized typename, prefix ``'Struct'``
            Unions
                oocized typename, prefix ``'Union'``
            Enum
                oocized typename, prefix ``'Enum'``
            Typedef
                oocized typename
            Function
                oocized name
        """
        if obj['class'] == 'Typedef':
            name = obj['tag']
        else:
            name = obj['name']

        if name.startswith('!Unnamed'):
            name = name.replace('!', '')
        elif name.startswith('!'):
            raise WTFError('WTF is this? %s %r' % (args[0], obj))
        
        def _struct():
            return 'Struct%s' % oocize_type(name)

        def _union():
            return 'Union%s' % oocize_type(name)

        def _enum():
            return 'Enum%s' % oocize_type(name)

        def _typedef():
            return oocize_type(name)

        def _function():
            return oocize_name(name)

        return {
                'Struct': _struct,
                'Union': _union,
                'Enum': _enum,
                'Typedef': _typedef,
                'Function': _function,
        }[obj['class']]()

    def generate_c_name(self, obj):
        """
            Return the C name of the babbisch object *obj*. If naming is
            impossible (e.g. for unnamed structs), raise ``NamingImpossibleError``.
        """
        # For structs and unions, it's just "struct %s" or "enum %s"
        if obj['class'] in ('Struct', 'Union'):
            mod, args = parse_string(obj['tag'])

            # Is it unnamed?
            if args[0].startswith('!Unnamed'):
                raise NamingImpossibleError("Can't be named: %r" % obj)
            elif args[0].startswith('!'):
                raise WTFError('WTF is this? %s %r' % (args[0], obj))

            # Okay. Please do it.
            def _struct():
                return 'struct %s' % obj['name']

            def _union():
                return 'union %s' % obj['name']

            return {
                'Struct': _struct,
                'Union': _union,
            }[obj['class']]()
        # For typedefs, it's just the tag (name).
        elif obj['class'] == 'Typedef':
            return obj['tag']
        # For enums, it's `int`.
        elif obj['class'] == 'Enum':
            return 'int'
        # For functions, it's the name.
        elif obj['class'] == 'Function':
            return obj['name']
        else:
            raise WTFError('Unknown type: %r' % obj)

    def create_ooc_names(self):
        """
            Generate ooc-suitable names for all objects in `self.objects`
            (except primitives).
            They are stored inside the object as a new value; the key
            is ``ooc_name``.
        """
        for tag, obj in self.objects.iteritems():
            if obj['class'] != 'Primitive':
                # generate a name for it and save it.
                name = self.generate_ooc_name(obj)
                obj['ooc_name'] = name

    def create_c_names(self):
        """
            Generate the C names for all objects in `self.objects` (except
            primitives).
            They are stored inside the object as a new value; the key is
            `c_name``.  If that is not possible (e.g. for unnamed structs),
            set ``c_name`` to ``None``.
        """
        for tag, obj in self.objects.iteritems():
            if obj['class'] != 'Primitive':
                # generate a name for it and save it.
                try:
                    name = self.generate_c_name(obj)
                except NamingImpossibleError:
                    name = None
                obj['c_name'] = name

    def generate_types(self):
        """
            Generate code for all types (e.g. everything but functions).
        """
        for tag, obj in self.objects.iteritems():
            if obj['class'] not in ('Function',):
                self.generate_type(obj)

    def generate_functions(self):
        """
            Generate code for all functions.
        """
        for tag, obj in self.objects.iteritems():
            if obj['class'] in ('Function',):
                self.generate_function(obj)

    def generate_function(self, obj):
        """
            generate the code for this function!
        """
        name = oocize_name(obj['name'])
        if obj['name'] == name:
            mod = 'extern'
        else:
            mod = 'extern(%s)' % (obj['name'] or '_')
        func = Function(name, modifiers=(mod,))
        # create a method object and add all tags
        for idx, (argname, argtype) in enumerate(obj['arguments']):
            if argname.startswith('!Unnamed'):
                argname = 'arg%d' % idx
            argname = oocize_name(argname)
            func.arguments[argname] = self.get_ooc_type(argtype)
        # add varargs
        if obj['varargs']:
            func.varargs = True
        # construct the glue code
        func.rettype = self.get_ooc_type(obj['rettype'])
        # yay, is a wrapper.
        self.add_wrapper(obj, func)

    def generate_type(self, obj):
        """
            Generate code for the type described in the babbisch object *obj*.
            The created codegen object will be added to *obj*, connected to
            the key ``codegen``, and to `self.codegens`, connected to the
            actual ooc type name (``obj['ooc_name']``).
        """
        {
            'Struct': self.generate_struct,
            'Union': self.generate_union,
            'Typedef': self.generate_typedef,
            'Primitive': lambda x: None, # yep, no-op
        }[obj['class']](obj)

    def generate_struct(self, obj):
        """
            Generate the wrapper for the babbisch struct *obj*.
        """
        if obj['c_name'] is None:
            wrapper = Cover(obj['ooc_name'])
        else:
            wrapper = Cover(obj['ooc_name'], obj['c_name'])
        # Yo, set everything up.
        wrapper.modifiers = ('extern',)
        # Give me members!
        for name, type, bitsize in obj['members']:
            assert bitsize is None # TODO TODO TODO
            new_name = oocize_name(name)
            typename = ''
            if new_name != name:
                typename += 'extern(%s)' % (name or '_')
            else:
                typename += 'extern'
            typename += ' %s' % self.get_ooc_type(type)
            wrapper.add_member(Attribute(new_name, typename))
        # Wrappypappy!
        self.add_wrapper(obj, wrapper)

    def generate_union(self, obj):
        """
            Generate the wrapper for the babbisch union *obj*.
        """
        if obj['c_name'] is None:
            wrapper = Cover(obj['ooc_name'])
        else:
            wrapper = Cover(obj['ooc_name'], obj['c_name'])
        # Yo, set everything up.
        wrapper.modifiers = ('extern',)
        # Give me members!
        for name, type in obj['members']:
            new_name = oocize_name(name)
            typename = ''
            if new_name != name:
                typename += 'extern(%s)' % (name or '_')
            else:
                typename += 'extern'
            typename += ' %s' % self.get_ooc_type(type)
            wrapper.add_member(Attribute(new_name, typename))
        # Wrappypappy!
        self.add_wrapper(obj, wrapper)

    def generate_typedef(self, obj):
        """
            Generate the wrapper for the babbisch typedef *obj*.
            It is a simple `X: extern cover from Y`, where `Y`
            is the C type of the target tag, or, if possible, the
            ooc name of the target tag.
        """
        if self.is_wrapped(obj['target']):
            # already wrapped.
            wrapper = Cover(obj['ooc_name'], self.objects[obj['target']]['ooc_name'])
        else:
            # not wrapped.
            wrapper = Cover(obj['ooc_name'], self.objects[obj['target']]['c_name'])
        wrapper.modifiers = ('extern',)
        self.add_wrapper(obj, wrapper)

def main():
    interface = None
    try:
        filename = sys.argv[1]
    except IndexError:
        print 'Usage: babbisch-ooc interface.yaml'
        return 1

    with open(filename, 'r') as f:
        interface = yaml.load(f)
    # load all objects
    objects = odict()
    for filename in interface.get('Files', ()):
        with open(filename, 'r') as f:
            objects.update(json.load(f))
    # create an oo client
    client = OOClient(objects, interface)
    print client.run()

