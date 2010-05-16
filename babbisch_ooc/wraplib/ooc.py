from babbisch.odict import odict
from .codegen import CodegenBase, INDENT, DEDENT

class Function(CodegenBase):
    def __init__(self, name, modifiers=None, args=None, rettype=None, code=None):
        if modifiers is None:
            modifiers = []
        if args is None:
            args = odict()
        if code is None:
            code = []
        suffix = ''
        if '~' in name:
            name, suffix = [i.strip() for i in name.split('~', 1)]
        self.name = name
        self.modifiers = modifiers
        self.arguments = args
        self.rettype = rettype
        self.code = code
        self.suffix = suffix
        self.varargs = False

    def generate_code(self):
        if self.modifiers:
            string = '%s: %s func' % (self.name, ' '.join(self.modifiers))
        else:
            string = '%s: func' % self.name
        if self.suffix:
            string += ' ~%s' % self.suffix
        args = ['%s: %s' % (name, type) for name, type in self.arguments.iteritems()]
        if self.varargs:
            args.append('...')
        if args:
            string += ' (%s)' % (', '.join(args))
        if (self.rettype and self.rettype != 'Void'):
            string += ' -> %s' % self.rettype
        if self.code:
            string += ' {'
        code = [string]
        if self.code:
            code.append(INDENT)
            code.extend(self.code)
            code.append(DEDENT)
            code.append('}')
        return code

class Method(Function):
    pass

class Attribute(CodegenBase):
    def __init__(self, name, typename, value=''):
        self.name = name
        self.typename = typename
        self.value = value

    def generate_code(self):
        line = '%s: %s' % (self.name, self.typename)
        if self.value:
            line += ' = %s' % self.value
        return line

class Cover(CodegenBase):
    def __init__(self, name, from_='', extends='', modifiers=None):
        self.name = name
        self.from_ = from_
        if modifiers is None:
            modifiers = []
        self.members = []
        self.modifiers = modifiers
        self.extends = extends

    def get_member_by_name(self, name):
        for member in self.members:
            if member.name == name:
                return member
        raise KeyError(name)

    def has_member(self, name):
        try:
            self.get_member_by_name(name)
            return True
        except KeyError:
            return False

    def generate_code(self):
        if self.modifiers:
            line = '%s: %s cover' % (self.name, ' '.join(self.modifiers))
        else:
            line = '%s: cover' % self.name
        if self.from_:
            line += ' from %s' % self.from_
        if self.extends:
            line += ' extends %s' % self.extends
        if self.members:
            line += ' {'
        code = [line]
        if self.members:
            code.extend([INDENT, self.members, DEDENT, '}'])
        code.append('') # empty line :)
        return code

    def add_member(self, member):
        self.members.append(member)

class Class(CodegenBase):
    def __init__(self, name, extends=''):
        self.name = name
        self.members = []
        self.extends = extends

    def get_member_by_name(self, name):
        for member in self.members:
            if member.name == name:
                return member
        raise KeyError(name)

    def has_member(self, name):
        try:
            self.get_member_by_name(name)
            return True
        except KeyError:
            return False

    def generate_code(self):
        line = '%s: class' % self.name
        if self.extends:
            line += ' extends %s' % self.extends
        line += ' {'
        return ([line, INDENT, self.members, DEDENT, '}', ''])

    def add_member(self, member):
        self.members.append(member)

class Enum(CodegenBase):
    def __init__(self, name, modifiers=None):
        self.name = name
        self.values = odict()
        if modifiers is None:
            modifiers = []
        self.modifiers = modifiers

    def generate_code(self):
        if self.modifiers:
            line = '%s: %s enum' % (self.name, ' '.join(self.modifiers))
        else:
            line = '%s: enum' % self.name
        line += ' {'
        code = [line, INDENT]
        for name, value in self.values.iteritems():
            if value is None:
                code.append(name)
            else:
                code.append('%s = %s' % (name, value))
        code.extend([DEDENT, '}'])
        return code

    def add_value(self, name, value=None):
        self.values[name] = value

