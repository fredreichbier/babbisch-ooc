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

    def add_wrapper(self, obj, wrapper):
        """
            Set *obj* the wrapper codegen of *wrapper*.
            Do two things:
             1) set ``obj['wrapper'] = wrapper``
             2) append *wrapper* to `self.codegens`
        """
        obj['wrapper'] = self.codegens[wrapper.name] = wrapper

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
        return 'wrapper' in self.objects[tag]

    def run(self):
        """
            Run the binding generator.

            Generating object oriented bindings is done in these steps:

             1) Create ooc names for all objects (:meth:`create_ooc_names`)
             2) Create C names for all objects (:meth:`create_c_name`)
             3) Generate code for types (structs, unions, enums, typedefs)
             4) Generate aaaaallllll code and return it as string.

        """
        self.create_ooc_names()
        self.create_c_names()
        self.generate_types()
        return self.generate_code()

    def generate_code(self):
        """
            Return the generated code as string.
        """
        return Codegen()(self.codegens.values()).buf

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
            Generate ooc-suitable names for all objects in `self.objects`.
            They are stored inside the object as a new value; the key
            is ``ooc_name``.
        """
        for tag, obj in self.objects.iteritems():
            # generate a name for it and save it.
            name = self.generate_ooc_name(obj)
            obj['ooc_name'] = name

    def create_c_names(self):
        """
            Generate the C names for all objects in `self.objects`.
            They are stored inside the object as a new value; the key is
            `c_name``.  If that is not possible (e.g. for unnamed structs),
            set ``c_name`` to ``None``.
        """
        for tag, obj in self.objects.iteritems():
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

    def generate_type(self, obj):
        """
            Generate code for the type described in the babbisch object *obj*.
            The created codegen object will be added to *obj*, connected to
            the key ``codegen``, and to `self.codegens`, connected to the
            actual ooc type name (``obj['ooc_name']``).
        """
        {
            'Struct': self.generate_struct,
            'Typedef': self.generate_typedef,
        }[obj['class']](obj)

    def generate_struct(self, obj):
        """
            Generate the wrapper for the babbisch struct *obj*.
        """
        if obj['c_name'] is None:
            # TODO: what to do for unnamed structs? hmmmm ...
            wrapper = Cover(obj['ooc_name'])
        else:
            wrapper = Cover(obj['ooc_name'], obj['c_name'])
        # Yo, set everything up.
        wrapper.modifiers = ('extern',)
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
            wrapper = Cover(obj['ooc_name'], self.get_wrapper(obj['target']).name)
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

