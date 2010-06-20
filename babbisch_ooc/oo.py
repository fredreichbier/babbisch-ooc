import re
import yaml

from .wraplib.ooc import Cover, Method, Function, Attribute, Class, Enum
from .names import oocize_name

class ObjectingError(Exception):
    pass

class Matcher(object):
    def match(self, client, obj):
        raise NotImplementedError()

    def __setstate__(self, dct):
        self.set_default()
        self.__dict__.update(dct)

class ArgumentMatcher(yaml.YAMLObject, Matcher):
    yaml_tag = u'!Argument'

    def set_default(self):
        self.modifier = None
        self.matches_tag = ''
        self.pos = 0

    def match(self, client, owner, obj):
        if obj['class'] != 'Function':
            return False
        args = obj['arguments']
        if self.pos >= len(args):
            return False
        if args[self.pos][1] == self.matches_tag:
            self.modifier.modify(client, owner, obj)
            return True
        else:
            return False

class Modifier(object):
    def modify(self, client, obj):
        raise NotImplementedError()

    def __setstate__(self, dct):
        self.set_default()
        self.__dict__.update(dct)

class MethodModifier(yaml.YAMLObject, Modifier):
    yaml_tag = u'!Method'

    def set_default(self):
        self.static = False
        self.this = 0
        self.regex = ''
        self.oocize = True

    def modify(self, client, owner, obj):
        wrapper = obj['wrapper']
        # No top-level codegen anymore.
        client.remove_wrapper(wrapper)
        # New name, baby.
        new_name_match = re.match(self.regex, obj['name'])
        if new_name_match is None:
            raise ObjectingError('%r did not match %r' % (obj['name'], self.regex))
        wrapper.name = new_name_match.group(1)
        if self.oocize:
            wrapper.name = oocize_name(wrapper.name)
        # Also new owner.
        owner.add_member(wrapper)
        # Static?
        if self.static:
            wrapper.modifiers.append('static')
        else:
            # have to remove `this`, then.
            try:
                key = wrapper.arguments.keys()[self.this]
                del wrapper.arguments[key]
            except KeyError:
                raise ObjectingError(
                    'Could not remove argument %d from arguments %r' % (self.this, wrapper.arguments)
                )
            pass
        print 'wuzziwuzzi. %r %r %r' % (owner, client, obj)

class OOInfo(object):
    def __init__(self, client):
        self.client = client

    def _(self):
        for name, info in client.interface.get('Objects', {}).iteritems():
            # Make a from type.
            from_type = ''
            if 'From' in info:
                from_type = client.get_ooc_type(info['From'])
            # Is it wrapped already?
            if name in client.codegens:
                # Yes it is. Use this wrapper.
                wrapper = client.codegens[name]
                # Replace from type if given.
                if from_type:
                    wrapper.from_ = from_type
            else:
                # No. create one.
                wrapper = Cover(name, from_type)
                client.codegens[name] = wrapper
            matchers = info.get('Matchers', [])
            # all objects yay!
            for obj in client.objects.itervalues():
                for matcher in matchers:
                    if matcher.match(client, wrapper, obj):
                        break
                else:
                    pass

