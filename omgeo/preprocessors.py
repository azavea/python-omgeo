from omgeo.processor import _Processor
import re


class _PreProcessor(_Processor):
    """Takes, processes, and returns a geocoding.places.PlaceQuery object."""
    def process(self, pq):
        raise NotImplementedError(
            'PreProcessor subclasses must implement process().')


class ReplaceRangeWithNumber(_PreProcessor):
    """
    Class to take only the first part of an address range
    or hyphenated house number to use for geocoding.

    This affects the query and address PlaceQuery attributes.

    =============================== ========================================
    Input                           Output
    =============================== ========================================
    ``4109-4113 Main St``           ``4109 Main St``
    ``4109-13 Main St``             ``4109 Main St``
    ``322-1/2 Water Street``        ``322 Water Street``
    ``123-2 Maple Lane``            ``123 Maple Lane``
    ``272-B Greenough St, 19127``   ``272 Greenough St, 19127``
    ``272 Greenough St 19127-1112`` ``272 Greenough St 19127-1112``
    ``19127-1112``                  ``19127-1112`` (not affected)
    ``76-20 34th Ave, Queens NY``   ``76 34th Ave, Queens NY`` (see warning)
    =============================== ========================================

    .. warning::

       This may cause problems with addresses presented in the
       hyphenated Queens-style format, where the part before the
       hyphen indicates the cross street, and the part after
       indicates the house number.
    """

    #: Regular expression to represent ranges like:
    #:  * 789-791
    #:  * 789-91
    #:  * 201A-201B
    #:  * 201A-B
    RE_STREET_NUMBER = re.compile('(^\d+\w*-\d*\w*)\s', re.IGNORECASE)

    def replace_range(self, addr_str):
        match = self.RE_STREET_NUMBER.match(addr_str)
        if match is not None:
            old = match.group(1)
            new = old.split('-', 1)[0]
            addr_str = addr_str.replace(old, new, 1)
        return addr_str

    def process(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery instance
        :returns: PlaceQuery instance with truncated address range / number
        """
        pq.query = self.replace_range(pq.query)
        pq.address = self.replace_range(pq.address)
        return pq


class ParseSingleLine(_PreProcessor):
    """
    Adapted from `Cicero Live <http://azavea.com/packages/azavea_cicero/blocks/cicero_live/view.js>`_
    """
    # Some Regexes:
    re_unit_numbered = re.compile('(su?i?te|p\W*[om]\W*b(?:ox)?|(?:ap|dep)(?:ar)?t(?:me?nt)?|ro*m|flo*r?|uni?t|bu?i?ldi?n?g|ha?nga?r|lo?t|pier|slip|spa?ce?|stop|tra?i?le?r|bo?x|no\.?)\s+|#', re.IGNORECASE)
    re_unit_not_numbered = re.compile('ba?se?me?n?t|fro?nt|lo?bby|lowe?r|off?i?ce?|pe?n?t?ho?u?s?e?|rear|side|uppe?r', re.IGNORECASE)
    re_UK_postcode = re.compile('[A-Z]{1,2}[0-9R][0-9A-Z]? *[0-9][A-Z]{0,2}', re.IGNORECASE)
    re_blank = re.compile('\s')

    def _comma_join(self, left, right):
        if left == '':
            return right
        else:
            return '%s, %s' % (left, right)

    def process(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery instance
        :returns: PlaceQuery instance with :py:attr:`query`
                  converted to individual elements
        """
        if pq.query != '':
            postcode = address = city = ''  # define the vars we'll use

            # global regex postcode search, pop off last result
            postcode_matches = self.re_UK_postcode.findall(pq.query)
            if len(postcode_matches) > 0:
                postcode = postcode_matches[-1]

            query_parts = [part.strip() for part in pq.query.split(',')]

            if postcode is not '' and re.search(postcode, query_parts[0]):
                # if postcode is in the first part of query_parts, there are probably no commas
                # get just the part before the postcode
                part_before_postcode = query_parts[0].split(postcode)[0].strip()
                if self.re_blank.search(part_before_postcode) is None:
                    address = part_before_postcode
                else:
                    address = query_parts[0]  # perhaps it isn't really a postcode (apt num, etc)
            else:
                address = query_parts[0]  # no postcode to worry about

            for part in query_parts[1:]:
                part = part.strip()
                if postcode is not '' and re.search(postcode, part) is not None:
                    part = part.replace(postcode, '').strip()  # if postcode is in part, remove it

                if self.re_unit_numbered.search(part) is not None:
                    # test to see if part is secondary address, like "Ste 402"
                    address = self._comma_join(address, part)
                elif self.re_unit_not_numbered.search(part) is not None:
                    # ! might cause problems if 'Lower' or 'Upper' is in the city name
                    # test to see if part is secondary address, like "Basement"
                    address = self._comma_join(address, part)
                else:
                    city = self._comma_join(city, part)  # it's probably a city (or "City, County")
            # set pq parts if they aren't already set (we don't want to overwrite explicit params)
            pq.postal = pq.postal or postcode
            pq.address = pq.address or address
            pq.city = pq.city or city

        return pq


class ComposeSingleLine(_PreProcessor):
    """ Compose address components into a single-line query if no query is already defined. """
    def process(self, pq):
        if pq.query == '':
            parts = [pq.address, pq.city, pq.subregion]
            parts.append(' '.join([p for p in (pq.state, pq.postal) if p != '']))
            if pq.country != '':
                parts.append(pq.country)
            pq.query = ', '.join([part for part in parts if part != ''])

        return pq


class CountryPreProcessor(_PreProcessor):
    """
    Used to filter acceptable countries
    and standardize country names or codes.
    """

    def __init__(self, acceptable_countries=None, country_map=None):
        """
        :arg list acceptable_countries: A list of acceptable countries.
                                        None is used to indicate that all countries are acceptable.
                                        (default ``[]``)

                                        An empty string is also an acceptable country. To require
                                        a country, use the `RequireCountry` preprocessor.

        :arg dict country_map: A map of the input PlaceQuery.country property
                               to the country value accepted by the geocoding service.

                               For example, suppose that the geocoding service recognizes
                               'GB', but not 'UK' -- and 'US', but not 'USA'::

                                    country_map = {'UK':'GB', 'USA':'US'} 

        """
        self.acceptable_countries = acceptable_countries if acceptable_countries is not None else []
        self.country_map = country_map if country_map is not None else {}

    def process(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery instance
        :returns: modified PlaceQuery, or ``False`` if country is not acceptable.
        """
        # Map country, but don't let map overwrite
        if pq.country not in self.acceptable_countries and pq.country in self.country_map:
            pq.country = self.country_map[pq.country]
        if pq.country != '' and \
           self.acceptable_countries != [] and \
           pq.country not in self.acceptable_countries:
            return False
        return pq

    def __repr__(self):
        return '<%s: Accept %s mapped as %s>' % (self.__class__.__name__,
                                                 self.acceptable_countries, self.country_map)


class CancelIfRegexInAttr(_PreProcessor):
    """
    Return False if given regex is found in ANY of the given
    PlaceQuery attributes, otherwise return original PlaceQuery instance.
    In the event that a given attribute does not exist in the given
    PlaceQuery, no exception will be raised.
    """
    def __init__(self, regex, attrs, ignorecase=True):
        """
        :arg str regex: a regex string to match (represents what you do *not* want)
        :arg attrs: a list or tuple of strings of attribute names to look through
        :arg bool ignorecase: set to ``False`` for a case-sensitive match (default ``True``)
        """
        regex_type = type(regex)
        if type(regex) not in (str, unicode):
            raise Exception('First param "regex" must be a regex of type'
                            ' str or unicode, not %s.' % regex_type)
        attrs_type = type(attrs)
        if attrs_type not in (list, tuple):
            raise Exception('Second param "attrs" must be a list or tuple'
                            ' of PlaceQuery attributes, not %s.' % attrs_type)
        if any(type(attr) not in (str, unicode) for attr in attrs):
            raise Exception('All given PlaceQuery attributes must be strings.')
        self.attrs = attrs
        if ignorecase:
            self.regex = re.compile(regex, re.IGNORECASE)
        else:
            self.regex = re.compile(regex)

    def process(self, pq):
        attrs = [getattr(pq, attr) for attr in self.attrs if hasattr(pq, attr)]
        if any([self.regex.match(attr) is not None for attr in attrs]):
            return False  # if a match is found
        return pq

    def __repr__(self):
        case_sensitive = 'insensitive' if self.ignorecase else 'sensitive'
        return '<%s: Break if %s in %s (case %s)>' % (self.__class__.__name__,
                                                      self.regex, self.attrs, case_sensitive)


class CancelIfPOBox(_PreProcessor):
    def process(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery instance
        :returns: ``False`` if the address is starts with any variation of "PO Box".
                  Otherwise, return original :py:class:`PlaceQuery`.
        """
        regex = r'^\s*P\.?\s*O\.?\s*B\.?O?X?[\s\d]'
        return CancelIfRegexInAttr(regex, ('address', 'query')).process(pq)


class RequireCountry(_PreProcessor):
    """
    Return False if no default country is set in first parameter.
    Otherwise, return the default country if country is empty.
    """
    def __init__(self, default_country=''):
        """
        :arg str default_country: default country to use if there is
                                  no country set in the PlaceQuery instance sent to this processor.
                                  If this argument is not set or empty and PlaceQuery instance does
                                  not have a country (pq.country == ''), the processor will return
                                  False and the PlaceQuery will be rejected during geocoding.
                                  (default ``''``)

        """
        self.default_country = default_country

    def process(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery instance
        :returns: One of the three following values:
                   * unmodified PlaceQuery instance if pq.country is not empty
                   * PlaceQuery instance with pq.country changed to default country.
                   * ``False`` if pq.country is empty and self.default_country == ''.
        """
        if pq.country.strip() == '':
            if self.default_country == '':
                return False
            else:
                pq.country = self.default_country
        return pq
