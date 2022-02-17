from functools import singledispatch

basestring = (str, bytes)

__all__ = [
    'partition', 'remove_null_bool', 'remove_empty_string'
]


def is_iterable(obj):
    """Similar in nature to :func:`callable`, ``is_iterable`` returns
    ``True`` if an object is `iterable`_, ``False`` if not.

    >>> is_iterable([])
    True
    >>> is_iterable(object())
    False

    .. _iterable: https://docs.python.org/2/glossary.html#term-iterable
    """
    try:
        iter(obj)
    except TypeError:
        return False
    return True


def bucketize(src, key=bool, value_transform=None, key_filter=None):
    """Group values in the *src* iterable by the value returned by *key*.

    >>> bucketize(range(5))
    {False: [0], True: [1, 2, 3, 4]}
    >>> is_odd = lambda x: x % 2 == 1
    >>> bucketize(range(5), is_odd)
    {False: [0, 2, 4], True: [1, 3]}

    *key* is :class:`bool` by default, but can either be a callable or a string or a list
    if it is a string, it is the name of the attribute on which to bucketize objects.

    >>> bucketize([1+1j, 2+2j, 1, 2], key='real')
    {1.0: [(1+1j), 1], 2.0: [(2+2j), 2]}

    if *key* is a list, it contains the buckets where to put each object

    >>> bucketize([1,2,365,4,98],key=[0,1,2,0,2])
    {0: [1, 4], 1: [2], 2: [365, 98]}


    Value lists are not deduplicated:

    >>> bucketize([None, None, None, 'hello'])
    {False: [None, None, None], True: ['hello']}

    Bucketize into more than 3 groups

    >>> bucketize(range(10), lambda x: x % 3)
    {0: [0, 3, 6, 9], 1: [1, 4, 7], 2: [2, 5, 8]}

    ``bucketize`` has a couple of advanced options useful in certain
    cases.  *value_transform* can be used to modify values as they are
    added to buckets, and *key_filter* will allow excluding certain
    buckets from being collected.

    >>> bucketize(range(5), value_transform=lambda x: x*x)
    {False: [0], True: [1, 4, 9, 16]}

    >>> bucketize(range(10), key=lambda x: x % 3, key_filter=lambda k: k % 3 != 1)
    {0: [0, 3, 6, 9], 2: [2, 5, 8]}

    Note in some of these examples there were at most two keys, ``True`` and
    ``False``, and each key present has a list with at least one
    item. See :func:`partition` for a version specialized for binary
    use cases.

    """
    if not is_iterable(src):
        raise TypeError('expected an iterable')
    elif isinstance(key, list):
        if len(key) != len(src):
            raise ValueError("key and src have to be the same length")
        src = zip(key, src)

    if isinstance(key, basestring):
        key_func = lambda x: getattr(x, key, x)
    elif callable(key):
        key_func = key
    elif isinstance(key, list):
        key_func = lambda x: x[0]
    else:
        raise TypeError('expected key to be callable or a string or a list')

    if value_transform is None:
        value_transform = lambda x: x
    if not callable(value_transform):
        raise TypeError('expected callable value transform function')
    if isinstance(key, list):
        f = value_transform
        value_transform = lambda x: f(x[1])

    ret = {}
    for val in src:
        key_of_val = key_func(val)
        if key_filter is None or key_filter(key_of_val):
            ret.setdefault(key_of_val, []).append(value_transform(val))
    return ret


def partition(src, key=bool):
    """No relation to :meth:`str.partition`, ``partition`` is like
    :func:`bucketize`, but for added convenience returns a tuple of
    ``(truthy_values, falsy_values)``.

    >>> nonempty, empty = partition(['', '', 'hi', '', 'bye'])
    >>> nonempty
    ['hi', 'bye']

    *key* defaults to :class:`bool`, but can be carefully overridden to
    use either a function that returns either ``True`` or ``False`` or
    a string name of the attribute on which to partition objects.

    >>> import string
    >>> is_digit = lambda x: x in string.digits
    >>> decimal_digits, hexletters = partition(string.hexdigits, is_digit)
    >>> ''.join(decimal_digits), ''.join(hexletters)
    ('0123456789', 'abcdefABCDEF')
    """
    bucketized = bucketize(src, key)
    return bucketized.get(True, []), bucketized.get(False, [])


@singledispatch
def remove_null_bool(ob):
    return ob


@remove_null_bool.register(list)
def _process_list(ob):
    return [remove_null_bool(v) for v in ob if v is not None]


@remove_null_bool.register(dict)
def _process_list(ob):
    return {k: remove_null_bool(v) for k, v in ob.items() if v is not None}


@singledispatch
def remove_empty_string(ob):
    return ob


@remove_empty_string.register(list)
def _process_list(ob):
    return [remove_null_bool(v) for v in ob if v != '']


@remove_empty_string.register(dict)
def _process_list(ob):
    return {k: remove_null_bool(v) for k, v in ob.items() if v != ''}

