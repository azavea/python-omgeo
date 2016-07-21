import re

from base import GeocodeService
import logging
from omgeo.places import Candidate

logger = logging.getLogger(__name__)


class USCensus(GeocodeService):

    # set endpoint based on whether we geocode by single-line address, or with keyed components
    _endpoint = ''
    _endpoint_base = 'http://geocoding.geo.census.gov/geocoder/locations/'

    def _geocode(self, pq):
        query = {
            'format': 'json',
            'benchmark': 'Public_AR_Current'
        }

        if pq.query:
            _this_endpoint = '%s%s' % (self._endpoint_base, 'onelineaddress')
            query['address'] = pq.query
        else:
            _this_endpoint = '%s%s' % (self._endpoint_base, 'address')
            query['street'] = pq.address
            query['city'] = pq.city
            query['state'] = pq.state
            query['zip'] = pq.postal

        logger.debug('CENSUS QUERY: %s', query)
        response_obj = self._get_json_obj(_this_endpoint, query)
        logger.debug('CENSUS RESPONSE: %s', response_obj)

        returned_candidates = []  # this will be the list returned
        for r in response_obj['result']['addressMatches']:
            c = Candidate()
            c.match_addr = r['matchedAddress']
            c.x = r['coordinates']['x']
            c.y = r['coordinates']['y']
            c.geoservice = self.__class__.__name__
            # Optional address component fields.
            for in_key, out_key in [('city', 'match_city'), ('state', 'match_region'),
                                    ('zip', 'match_postal')]:
                setattr(c, out_key, r['addressComponents'].get(in_key, ''))
            setattr(c, 'match_subregion', '')  # No county from Census geocoder.
            setattr(c, 'match_country', 'USA')  # Only US results from Census geocoder
            setattr(c, 'match_streetaddr', self._street_addr_from_response(r))
            returned_candidates.append(c)
        return returned_candidates

    def _street_addr_from_response(self, match):
        """Construct a street address (no city, region, etc.) from a geocoder response.

        :param match: The match object returned by the geocoder.
        """
        # Same caveat as above regarding the ordering of these fields; the
        # documentation is not explicit about the correct ordering for
        # reconstructing a full address, but implies that this is the ordering.
        ordered_fields = ['preQualifier', 'preDirection', 'preType', 'streetName',
                          'suffixType', 'suffixDirection', 'suffixQualifier']
        result = []
        # The address components only contain a from and to address, not the
        # actual number of the address that was matched, so we need to cheat a
        # bit and extract it from the full address string. This is likely to
        # miss some edge cases (hopefully only a few since this is a US-only
        # geocoder).
        addr_num_re = re.match(r'([0-9]+)', match['matchedAddress'])
        if not addr_num_re:  # Give up
            return ''
        result.append(addr_num_re.group(0))
        for field in ordered_fields:
            result.append(match['addressComponents'].get(field, ''))
        if any(result):
            return ' '.join([s for s in result if s])  # Filter out empty strings.
        else:
            return ''
