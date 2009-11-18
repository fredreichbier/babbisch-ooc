import token
from tokenize import generate_tokens, untokenize
from StringIO import StringIO

class _Indent(object):
    def __repr__(self):
        return '<Indent instruction>'

class _Dedent(object):
    def __repr__(self):
        return '<Dedent instruction>'

INDENT = _Indent()
DEDENT = _Dedent()

class Codegen(object):
    def __init__(self):
        self.buf = ''
        self.indent_level = 0

    def __call__(self, fmt=''):
        if callable(fmt): # callable. call.
            self(fmt())
            return self
        elif isinstance(fmt, (list, tuple)):
            map(self, fmt)
            return self
        elif hasattr(fmt, 'generate_code'):
            self(fmt.generate_code())
            return self

        if fmt is INDENT:
            self.indent()
        elif fmt is DEDENT:
            self.dedent()
        else:
            if not fmt:
                self.buf += '\n' # no unneeded indentation spaces
            else:
                self.buf += '    ' * self.indent_level + fmt + '\n'
        return self

    def indent(self, level=1):
        self.indent_level += level
        return self

    def dedent(self, level=1):
        self.indent_level -= level
        return self

class CodegenBase(object):
    def generate_code(self):
        """
            returns a list of lines
        """
        raise NotImplementedError()

    def generate_docs(self):
        """
            returns a list of lines
        """
        raise NotImplementedError()

    def __call__(self):
        """
            a nice shortcut for `Codegen`.
        """
        return self.generate_code()

class DummyCodegen(CodegenBase):
    def __init__(self, **attrib):
        self.__dict__.update(attrib)

    def generate_code(self):
        return ''

    def generate_docs(self):
        return ''

def transform(src):
    result = []
    queue = []
    for tok in generate_tokens(StringIO(src).readline):
        if tok[0] in (token.INDENT, token.DEDENT, token.NEWLINE):
            string = untokenize(queue)
            if string:
                result.append(string)
            queue = []
            if tok[0] == token.INDENT:
                result.append(INDENT)
            elif tok[0] == token.DEDENT:
                result.append(DEDENT)
        else:
            queue.append(tok[:2])
    return result
