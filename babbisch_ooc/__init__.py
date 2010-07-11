import sys
import os.path
import re
from collections import defaultdict
from operator import itemgetter

import yaml

try:
    import simplejson as json
except ImportError:
    import json

from babbisch.tag import translate, parse_string
from babbisch.odict import odict

from .wraplib.codegen import Codegen
from .wraplib.ooc import Cover, Method, Function, Attribute, Class, Enum

from .types import TYPE_MAP
from .names import oocize_name, oocize_type, get_common_prefix
from .oo import OOInfo

IGNORED_HEADERS = map(re.compile,
    [
        '/usr/lib/gcc/.*',
        '/usr/include/bits/.*',
        '/usr/share/gccxml.*',
        '/usr/include/std.*',
        '/usr/include/_G_config.*',
    ]
)

class WTFError(Exception):
    pass

class NamingImpossibleError(Exception):
    pass

class MemberInfo(object):
    def __init__(self, this_tag, **p):
        self.this_tag = this_tag
        self.__dict__.update(p)

class MethodInfo(MemberInfo):
    pass

class OOClient(object):
    def __init__(self, objects, interface):
        #: list of header names
        self.headers = []
        #: object oriented information manager
        self.ooinfo = OOInfo(self)
        #: odict of babbisch objects.
        self.objects = objects
        #: Dictionary containing the user-defined YAML interface.
        self.interface = interface
        #: Dictionary mapping tag types to artificial wrapper (ooc) names.
        self.artificial = {}
        #: Dictionary mapping entity tags to to MemberInfo instances.
        self.members = {}
        #: odict {name: codegen} of artificial wrappers getting merged in `run`
        self._codegens = odict()
        #: odict {name: codegen} of *all* codegens.
        self.codegens = odict()
        # fill in all primitive types
        self.create_primitives()

    def has_member_info(self, member_tag):
        """
            Return True if there is a member info for the member tagged `member_tag`.
        """
        return member_tag in self.members

    def get_member_info(self, member_tag):
        """
            Return the member info for this member.
        """
        return self.members[member_tag]

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

    def add_artificial_cover(self, name, c_type, c_tag, extends=''):
        """
            Add an artificial cover named *name* for the tag *c_tag*
            (*c_type*) that extends *extends*. It will have priority
            over any covers of the same name or of the same type.
        """
        self.artificial[c_tag] = name
        self._codegens[name] = Cover(
            name=name,
            from_=c_type,
            extends=extends,
        )

    def add_method(self, function_tag, method_name, this_tag, this_idx=0):
        """
            Make a function appear in the output as a method.

            :Parameters:
                `function_tag`
                    Tag (name) of the function
                `method_name`
                    Desired method name.
                `this_tag`
                    Tag of the `this` type.
                `this_idx`
                    Index of the to-be-removed `this` argument.
        """
        self.members[function_tag] = MethodInfo(
            this_tag=this_tag,
            function_tag=function_tag,
            name=method_name,
            this_idx=this_idx,
        )

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

    def remove_wrapper(self, codegen):
        """
            This codegen should not generate code anymore.
        """
        del self.codegens[codegen.name]

    def get_wrapper(self, tag):
        """
            Get the wrapper of the object identified by the tag *tag*.
        """
        return self.objects[tag]['wrapper']

    def get_wrapper_by_name(self, name):
        """
            Get the wrapper. I know its name.
        """
        return self.codegens[name]

    def is_wrapped(self, tag):
        """
            Return a boolean value that describes whether the object with
            the tag *tag* is wrapped or not.
        """
        try:
            return self.objects[tag]['wrapped']
        except KeyError:
            return False

    def collect_headers(self):
        """
            Iterate over all objects and collect header filenames.
            Add the header codegen.
            This will not be cross-platform. Therefore, TODO!
        """
        headers = set()
        for obj in self.objects.itervalues():
            if 'coord' in obj:
                filename = obj['coord']['file']
                # check if it should be ignored.
                ignore = False
                for pattern in IGNORED_HEADERS:
                    if pattern.match(filename):
                        ignore = True
                if not ignore:
                    headers.add(filename)
        # Generate code.
        code = []
        for header in headers:
            name = os.path.splitext(header)[0]
            code.append('include %s' % name)
        code.append('')
        self.codegens['!headers'] = code

    def run(self):
        """
            Run the binding generator.

            Generating object oriented bindings is done in these steps:

             1) Collect header files and merge artificial wrappers.
             2) Create ooc names for all objects (:meth:`create_ooc_names`)
             3) Create C names for all objects (:meth:`create_c_name`)
             4) Generate code for types (structs, unions, enums, typedefs)
             5) Generate code for functions
             6) Generate aaaaallllll code and return it as string.

        """
        self.collect_headers()
        self.codegens.update(self._codegens)
        self.handle_opaque_types()
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

    def get_opaque_types(self):
        """
            yield tags of opaque (i.e. unknown) types.
        """
        for obj in self.objects.copy().itervalues():
            # only handle typedefs ...
            if obj['class'] == 'Typedef':
                # get the first, typedef tag
                tag = obj['target']
                while '(' in tag:
                    mod, args = parse_string(tag)
                    # is it wrapping a struct or union that is unknown?
                    if (mod in ('STRUCT', 'UNION')
                        and tag not in self.objects):
                        # then it's opaque.
                        yield tag
                        break
                    # proceed.
                    tag = translate(args[0])

    def handle_opaque_types(self):
        for tag in self.get_opaque_types():
            mod, args = parse_string(tag)
            # just create a "fake type".
            self.objects[tag] = {
                'tag': tag,
                'class': {'STRUCT': 'Struct', 'UNION': 'Union'}[mod],
                'name': args[0], # TODO?
                'members': [],
                'opaque': True,
            }
#            if mod == 'STRUCT':
#                self.generate_struct(obj)
#            else:
#                self.generate_union(obj)

    def get_ooc_type(self, tag):
        """
            get the ooc type from the tag *tag*. It might be nested.
            And might be a pointer. Or an array. Whatever! It can
            be *anything*!
        """
        # is it artificial? if yes, we already have a type.
        if tag in self.artificial:
            return self.artificial[tag]
        # is it an enum? TODO: not here, please :(
        elif tag.startswith('ENUM('):
            return 'Int'
        # is it a real object?
        elif tag in self.objects:
            return self.objects[tag]['ooc_name']
        # nope. :(
        else:
            if '(' in tag:
                mod, args = parse_string(tag)
                
                def _pointer():
                    # A pointer to a function type is a Func.
                    try:
                        if args[0][0] == 'FUNCTIONTYPE':
                            return 'Func'
                    except IndexError:
                        pass
                    try:
                        return self.get_ooc_type(translate(args[0])) + '*'
                    except WTFError:
                        # That might work well for unknown types.
                        # TODO: print a message to stderr
                        return 'Pointer'

                def _const():
                    return 'const %s' % self.get_ooc_type(translate(args[0]))

                def _array():
                    # TODO: that looks incorrect.
                    return self.get_ooc_type(translate(args[0])) + '*'

                def _ignore():
                    return self.get_ooc_type(translate(args[0]))

                def _functiontype():
                    return 'Func' # TODO: correct?

                try:
                    return {
                        'POINTER': _pointer,
                        'CONST': _const,
                        'ARRAY': _array,
                        'FUNCTIONTYPE': _functiontype,
                        # Ignore `volatile` + `restrict` storage type.
                        'VOLATILE': _ignore,
                        'RESTRICT': _ignore,
                    }[mod]()
                except KeyError:
                    raise WTFError('WTF tag is this? %r' % tag)
            else:
                #raise WTFError('WTF tag is this? %r' % tag)
                return 'Pointer' # TODO: not so good

    def generate_ooc_name(self, obj):
        """
            Return an appropriate ooc name for the object *obj*.

            If the user provides with a name in the interface, use this one.

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

        if obj['tag'] in self.interface.get('Names', {}):
            return self.interface['Names'][obj['tag']]

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
        if obj['class'] in ('Struct', 'Union', 'Enum'):
            mod, args = parse_string(obj['tag'])

            # Is it unnamed?
            if args[0].startswith('!Unnamed'):
                raise NamingImpossibleError("Can't be named: %r" % obj)
            elif args[0].startswith('!'):
                raise WTFError('WTF is this? %s %r' % (args[0], obj))

            # Is it opaque? If yes, don't create a C name, please.
            # Because if we do, it will appear in the C source, and
            # *_class() will do a sizeof(), and everyone will be sad :(
            if obj.get('opaque', False):
                raise NamingImpossibleError("Can't be named: %r" % obj)

            # Okay. Please do it.
            def _struct():
                return 'struct %s' % obj['name']

            def _union():
                return 'union %s' % obj['name']

            def _enum():
                return 'enum %s' % obj['name']

            return {
                'Struct': _struct,
                'Union': _union,
                'Enum': _enum,
            }[obj['class']]()
        # For typedefs, it's just the tag (name).
        elif obj['class'] == 'Typedef':
            return obj['tag']
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
        # is it a method?
        if self.has_member_info(obj['tag']):
            # Yes! Make it a method.
            member_info = self.get_member_info(obj['tag'])
            # First, remove the "this" argument.
            del func.arguments[func.arguments.keys()[member_info.this_idx]]
            # Then, change the name.
            func.name = member_info.name
            # Now, add it to a class. No need to make a `Method` here. (TODO?)
            this_wrapper = self.get_wrapper_by_name(member_info.this_tag)
            this_wrapper.add_member(func)
        else:
            # yay, is a top-level wrapper.
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
            'Enum': self.generate_enum,
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
        # Give me members!
        for name, type, bitsize in obj['members']:
            #assert bitsize is None # TODO TODO TODO
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
            # Enums are wrapped as classes, so don't use a cover here!
            if self.objects[obj['target']]['class'] == 'Enum':
                wrapper = Class(obj['ooc_name'], self.objects[obj['target']]['ooc_name'])
            else:
                wrapper = Cover(obj['ooc_name'], self.objects[obj['target']]['ooc_name'])
                #wrapper.modifiers = ('extern',)
        else:
            # not wrapped.
            if obj['target'] in self.objects:
                target_name = self.objects[obj['target']]['c_name']
            else:
                # most likely a compound type.
                target_name = self.get_ooc_type(obj['target'])
            wrapper = Cover(obj['ooc_name'], target_name)
            #wrapper.modifiers = ('extern',)
        self.add_wrapper(obj, wrapper)

    def generate_enum(self, obj):
        """
            Generate the wrapper for the babbisch enum *obj*.
        """
        if obj['c_name'] is not None:
            wrapper = Enum(obj['ooc_name'], ['extern(%s)' % obj['name']])
        else:
            wrapper = Enum(obj['ooc_name'])
        # try to get a prefix
        prefix = get_common_prefix(map(itemgetter(0), obj['members']))
        #if not prefix:
        #    print >>sys.stderr, "Could not find a common prefix for %s members" % obj['tag']
        # add members
        for name, value in obj['members']:
            name = oocize_name(name[len(prefix):])
            wrapper.add_value(name, str(value))
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
    client.add_artificial_cover('Person', 'Person*', 'POINTER(Person)')
    client.add_method('person_set_name', 'setName', 'Person', 0)
    print client.run()


