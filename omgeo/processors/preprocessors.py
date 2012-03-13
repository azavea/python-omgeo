from omgeo.processors import PreProcessor
import re

class ReplaceRangeWithNumber(PreProcessor):
    re_street_number = re.compile('\d+\w*-\d*\w*', re.IGNORECASE)
    """
    Regular expression to represent ranges like:
     * 789-791 
     * 789-91
     * 201A-201B
     * 201A-B
    """

    def replace_range(self, addr_str):
        match = self.re_street_number.match(addr_str)
        if match is not None:
            old = match.group(0)
            new = match.group(0).split('-', 1)[0]
            addr_str = addr_str.replace(old, new, 1)
        return addr_str

    def process(self, pq):
        """
        Return a PlaceQuery with ranges truncated to the first street number
        for its query and address properties.
        """
        pq.query = self.replace_range(pq.query)
        pq.address = self.replace_range(pq.address)                       
        return pq

class ParseSingleLine(PreProcessor):
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
        Takes QueryString object, breaks query out into address pieces,
        returns improved QueryString object.

        Adapted from azavea.com/packages/azavea_cicero/blocks/cicero_live/view.js
        """
        if pq.query != '':
            postcode = address = city = '' # define the vars we'll use

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
                    address = query_parts[0] #perhaps it isn't really a postcode (apt num, etc)
            else:
                address = query_parts[0] # no postcode to worry about
            
            for part in query_parts[1:]:
                part = part.strip()
                if postcode is not '' and re.search(postcode, part) is not None:
                    part = part.replace(postcode, '').strip() # if postcode is in part, remove it

                if self.re_unit_numbered.search(part) is not None:
                    # test to see if part is secondary address, like "Ste 402"
                    address = self._comma_join(address, part)
                elif self.re_unit_not_numbered.search(part) is not None:
                    # ! might cause problems if 'Lower' or 'Upper' is in the city name
                    # test to see if part is secondary address, like "Basement"
                    address = self._comma_join(address, part)
                else:
                    city = self._comma_join(city, part)# it's probably a city (or "City, County")                
            # set pq parts if they aren't already set (we don't want to overwrite explicit params)
            if pq.postal == '': pq.postal = postcode
            if pq.address == '': pq.address = address
            if pq.city == '': pq.city = city

        return pq

class CountryPreProcessor(PreProcessor):
    
    acceptable_countries = []
    """
    A list of acceptable countries.
    [] is used to indicate that all countries are acceptable.

    An empty string is also an acceptable country. To require
    a country, use the `RequireCountry` preprocessor.
    """

    country_map = {}
    """
    A map of the input PlaceQuery.country property
    to the country value accepted by the geocoding service.

    Example:
    ========
    Suppose that the geocoding service recognizes 'GB', but not 'UK',
    and 'US', but not 'USA':
    
        country_map = {'UK':'GB', 'USA':'US'}
    """

    def __init__(self, acceptable_countries=[], country_map={}):
        self._init_helper(vars())

    def process(self, pq):
        # Map country, but don't let map overwrite
        if pq.country not in self.acceptable_countries and \
           pq.country in self.country_map:
            pq.country = self.country_map[pq.country]
        if pq.country != '' and \
           self.acceptable_countries != [] and \
           pq.country not in self.acceptable_countries:
            return False
        return pq

class RequireCountry(PreProcessor):
    """
    Return False if no default country is set in first parameter.
    Otherwise, return the default country if country is empty.
    """
    def __init__(self, default_country=''):
        self._init_helper(vars())

    def process(self, pq):
        if pq.country.strip() == '':
            if self.default_country == '': return False
            else: pq.country = self.default_country
        return pq
