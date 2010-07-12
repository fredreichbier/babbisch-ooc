import re
from .names import oocize_name

def _get_matching_methods_by_name(client, object_name, matcher_info):
    # Collect regexes.
    regexes = []
    for regex in matcher_info:
        # User can give us the this index separated by a comma.
        if ',' in regex:
            # got this_idx
            regex, this_idx = regex.split(',', 1)
            this_idx = int(this_idx)
        else:
            this_idx = 0
        regexes.append((re.compile(regex), this_idx))
    # And collect!
    for obj in client.objects.itervalues():
        if obj['class'] == 'Function':
            for r, this_idx in regexes:
                match = r.match(obj['name'])
                if match is not None:
                    yield (obj, match.group(1), this_idx)

METHOD_MATCHERS = {
    'by_name': _get_matching_methods_by_name,
}

def _apply_methods(client, object_name, object_info):
    objects = set()
    # Static methods!
    for matcher, matcher_info in object_info.get('static_methods', {}).iteritems():
        for obj, method_name, this_idx in METHOD_MATCHERS[matcher](client, object_name, matcher_info):
            if obj['tag'] not in objects:
                objects.add(obj['tag'])
                # Add the method. We're just implicitly occizing the name. Evil, isn't it?
                client.add_method(obj['name'], oocize_name(method_name), object_name, static=True)
    # Methods!
    for matcher, matcher_info in object_info.get('methods', {}).iteritems():
        for obj, method_name, this_idx in METHOD_MATCHERS[matcher](client, object_name, matcher_info):
            if obj['tag'] not in objects:
                objects.add(obj['tag'])
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
