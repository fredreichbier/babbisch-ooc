import re

def upper_first(name):
    if not name:
        return name
    if name[0].islower():
        return name[0].upper() + name[1:]
    else:
        return name

def oocize_name(name):
    if not name:
        return '_' # TODO: that should not be necessary
    # lower first letters
    name = re.sub('^([A-Z]+)', lambda m: m.group(1).lower(), name)
    # set_this -> setThis
    # underscores at the start are kept.
    underscored = False
    if name.startswith('_') or name[0].isdigit():
        underscored = True
    name = re.sub('_([^_]*)', lambda m: upper_first(oocize_name(m.group(1))), name)
    if underscored:
        name = '_' + name
    return censor(name)

def oocize_type(name):
    if not name:
        return '_' # TODO: that should not be necessary  
    # set_this -> setThis
    # underscores at the start are kept.
    underscored = False
    if name.startswith('_') or name[0].isdigit():
        underscored = True
    name = re.sub('_([^_]*)', lambda m: upper_first(oocize_name(m.group(1))), name)
    if underscored:
        name = '_' + name
    return censor(upper_first(name))

KEYWORDS = 'class, cover, interface, implement, func, abstract, extends, from, this, super, new, const, final, static, include, import, use, extern, inline, proto, break, continue, fallthrough, operator, if, else, for, while, do, switch, case, as, in, version, return, true, false, null, default, match'.split(', ') + ["auto",
                "break",
                "case",
                "char",
                "const",
                "continue",
                "default",
                "do",
                "double",
                "else",
                "enum",
                "extern",
                "float",
                "for",
                "goto",
                "if",
                "int",
                "long",
                "register",
                "return",
                "short",
                "signed",
                "static",
                "struct",
                "switch",
                "typedef",
                "union",
                "unsigned",
                "void",
                "volatile",
                "while",
                "inline",
                "_Imaginary",
                "_Complex",
                "_Bool",
                "restrict", "Func", "NULL", "TRUE", "FALSE", "bool"]

def censor(name):
    if name in KEYWORDS:
        return censor(name + '_')
    else:
        return name

def get_common_prefix(names):
    prefix = ''
    first = names[0]
    if len(names) < 2:
        return prefix
    while len(prefix) < len(first):
        if all(n.startswith(prefix) for n in names):
            prefix = first[:len(prefix)+1]
        else:
            break
    return prefix[:-1]
