import re
from .names import oocize_name

import yaml

def _match_by_name(loader, node):
    """
        This can be followed by a mapping or a string (as a short-hand).
    """
    if isinstance(node, yaml.nodes.MappingNode):
        options = loader.construct_mapping(node)
        regex = re.compile(options['regex'])
        this_idx = int(options.get('this_idx', 0))
    else:
        regex = re.compile(loader.construct_scalar(node))
        this_idx = 0
    def matches(client, obj):
        match = regex.match(obj['name'])
        if match is not None:
            return (match.group(1), this_idx)
        else:
            return False
    return matches

def _match_by_tag(loader, node):
    """
        Mapping or string, baby.
    """
    if isinstance(node, yaml.nodes.MappingNode):
        options = loader.construct_mapping(node)
        tag = options['tag']
        this_idx = int(options.get('this_idx', 0))
        name_regex = re.compile(options['name_regex'])
    else:
        tag = loader.construct_scalar(node)
        this_idx = 0
        name_regex = re.compile('.*')
    def matches(client, obj):
        if len(obj['arguments']) <= this_idx:
            return False
        elif obj['arguments'][this_idx][1] == tag:
            return (name_regex.match(obj['name']).group(1), this_idx)
        else:
            return False
    return matches

yaml.add_constructor(u'!by_name', _match_by_name)
yaml.add_constructor(u'!by_tag', _match_by_tag)

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

def _apply_properties(client, object_name, object_info):
    for name, prop_info in object_info.get('properties', {}).iteritems():
        client.add_property(
            object_name,
            name,
            prop_info['type'],
            prop_info.get('getter'),
            prop_info.get('setter'),
            prop_info.get('static', False)
        )

def apply_settings(client):
    """
        Apply all oo settings.
    """
    # Add artificial covers.
    for object_name, info in client.interface.get('Objects', {}).iteritems():
        client.add_artificial_cover(object_name, info['type'], info['tag'], info.get('extends', ''))
        # Add methods.
        _apply_methods(client, object_name, info)
        # Properties.
        _apply_properties(client, object_name, info)
