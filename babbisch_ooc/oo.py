import re
from .names import oocize_name

import yaml

def _match_by_name(loader, node):
    value = loader.construct_scalar(node)
    if ',' in value:
        regex, this_idx = regex.split(',', 1)
        regex = re.compile(regex)
        this_idx = int(this_idx)
    else:
        regex = re.compile(value)
        this_idx = 0
    def matches(client, obj):
        match = regex.match(obj['name'])
        if match is not None:
            return (match.group(1), this_idx)
        else:
            return False
    return matches

yaml.add_constructor(u'!by_name', _match_by_name)

def _apply_methods(client, object_name, object_info):
    for obj in client.objects.itervalues():
        if obj['class'] == 'Function':
            wrapped = False
            # Static methods!
            for matcher in object_info.get('static_methods', ()):
                result = matcher(client, obj)
                if result:
                    method_name, this_idx = result
                    # Add the method. We're just implicitly occizing the name. Evil, isn't it?
                    client.add_method(obj['name'], oocize_name(method_name), object_name, static=True)
                    wrapped = True
                    break
            # Methods!
            if not wrapped:
                for matcher in object_info.get('methods', ()):
                    result = matcher(client, obj)
                    if result:
                        method_name, this_idx = result
                        # Add the method. We're just implicitly occizing the name. Evil, isn't it?
                        client.add_method(obj['name'], oocize_name(method_name), object_name, this_idx)

def apply_settings(client):
    """
        Apply all oo settings.
    """
    # Add artificial covers.
    for object_name, info in client.interface.get('Objects', {}).iteritems():
        client.add_artificial_cover(object_name, info['type'], info['tag'], info.get('extends', ''))
        # Add methods.
        _apply_methods(client, object_name, info)
