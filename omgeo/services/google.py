import logging

from .base import GeocodeService
from omgeo.places import Candidate
from omgeo.preprocessors import ComposeSingleLine

logger = logging.getLogger(__name__)


class Google(GeocodeService):
    """
    Class to geocode using Google's geocoding API.
    """
    _endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'

    DEFAULT_PREPROCESSORS = [ComposeSingleLine()]

    LOCATOR_MAPPING = {
        'ROOFTOP': 'rooftop',
        'RANGE_INTERPOLATED': 'interpolated',
    }

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = self.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

    def _geocode(self, pq):
        params = {
            'address': pq.query,
            'key': self._settings['api_key']
        }

        if pq.country:
            params['components'] = 'country:' + pq.country
        if pq.viewbox:
            params['bounds'] = pq.viewbox.to_google_str()

        response_obj = self._get_json_obj(self._endpoint, params)
        return [self._make_candidate_from_result(r) for r in response_obj['results']]

    def _make_candidate_from_result(self, result):
        """ Make a Candidate from a Google geocoder results dictionary. """
        candidate = Candidate()
        candidate.match_addr = result['formatted_address']
        candidate.x = result['geometry']['location']['lng']
        candidate.y = result['geometry']['location']['lat']
        candidate.locator = self.LOCATOR_MAPPING.get(result['geometry']['location_type'], '')
        candidate.partial_match = result.get('partial_match', False)

        component_lookups = {
            'city': {'type': 'locality', 'key': 'long_name'},
            'subregion': {'type': 'administrative_area_level_2', 'key': 'long_name'},
            'region': {'type': 'administrative_area_level_1', 'key': 'short_name'},
            'postal': {'type': 'postal_code', 'key': 'long_name'},
            'country': {'type': 'country', 'key': 'short_name'},
        }
        for (field, lookup) in component_lookups.iteritems():
            setattr(candidate, 'match_' + field, self._get_component_from_result(result, lookup))
        candidate.geoservice = self.__class__.__name__
        return candidate

    def _get_component_from_result(self, result, lookup):
        """
        Helper function to get a particular address component from a Google result.

        Since the address components in results are an array of objects containing a types array,
        we have to search for a particular component rather than being able to look it up directly.

        Returns the first match, so this should be used for unique component types (e.g.
        'locality'), not for categories (e.g. 'political') that can describe multiple components.

        :arg dict result: A results dict with an 'address_components' key, as returned by the
                          Google geocoder.
        :arg dict lookup: The type (e.g. 'street_number') and key ('short_name' or 'long_name') of
                          the desired address component value.
        :returns: address component or empty string
        """
        for component in result['address_components']:
            if lookup['type'] in component['types']:
                return component.get(lookup['key'], '')
        return ''
