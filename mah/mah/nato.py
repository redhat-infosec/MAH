"""
Nato alphabet mapping along with helper code to make the alphabet easy to use.
Attempts to extract unknown NATO words will result in the unknown word being
returned verbatim.

NATO source: https://en.wikipedia.org/wiki/NATO_phonetic_alphabet

    >>> from mah.nato import NATO
    >>> NATO['a']
    'Alpha'
    >>> NATO['A']
    'Alpha'
    >>> NATO['b']
    'Bravo'
    >>> NATO['.']
    'Decimal'
    >>> NATO['1']
    'One'
    >>> NATO['blah'] # Not a known NATO word
    'blah'
"""
class NATODict(dict):
    """
    A dictionary with case insensitive keys, and which will return the key name
    if the key is missing from the dict.

    For instance:
        >>> mydict = NATODict({'HI': 'there'})
        >>> print mydict['HI']
        there
        >>> print mydict['hi']
        there
        >>> print mydict['hI']
        there
        >>> print mydict['Hi']
        there
        >>> print mydict['Ha'] # 'ha' is not a known key
        Ha
    """
 
    # Canary object for the get method, since None is a valid default value
    _NO_VALUE = object()

    def __setitem__(self, key, value):
        """
        Handles item setting when NATODict[key] = value is used.

        :Parameters:
           - `key`: the key (which will be forced lowercase)
           - `value`: the value for the key (which will not change case)
        """
        super(NATODict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        """
        Handles item getting when value = NATODict[key] is used.
        If key.lower() does not exist in the NATODict, key is returned.

        :Parameters:
            - `key`: the key (which will be forced lowercase)
        """
        return self.get(key, key)

    def get(self, key, default=_NO_VALUE):
        """
        Returns the value stored for key.lower(). If the key is not in the dict,
        the key name is returned instead, unless a default value is given in
        which case that will be returned.

        :Parameters:
            - `key`: the key (which will be forced lowercase)
            - `default`: optional, a value to return if the key is not found,
                         defaults to key
        """
        if default == self.__class__._NO_VALUE:
            default = key
        return super(NATODict, self).get(key.lower(), default)

#: Source: https://en.wikipedia.org/wiki/NATO_phonetic_alphabet
NATO = NATODict({
  'a': 'Alpha',   'b': 'Bravo',  'c': 'Charlie', 'd': 'Delta',    'e': 'Echo',
  'f': 'Foxtrot', 'g': 'Golf',   'h': 'Hotel',   'i': 'India',    'j': 'Juliet',
  'k': 'Kilo',    'l': 'Lima',   'm': 'Mike',    'n': 'November', 'o': 'Oscar',
  'p': 'Papa',    'q': 'Quebec', 'r': 'Romeo',   's': 'Sierra',   't': 'Tango',
  'u': 'Uniform', 'v': 'Victor', 'w': 'Whiskey', 'x': 'Xray',     'y': 'Yankee',
  'z': 'Zulu',
  '0': 'Zero',    '1': 'One',    '2': 'Two',     '3': 'Three',    '4': 'Four',
  '5': 'Five',    '6': 'Six',    '7': 'Seven',   '8': 'Eight',    '9': 'Nine',
  '.': 'Decimal', '-': 'Dash'
})
