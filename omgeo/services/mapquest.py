from base import GeocodeService
import json
import logging
from omgeo.places import Candidate
from urllib import unquote

logger = logging.getLogger(__name__)


class MapQuest(GeocodeService):
    """
    Class to geocode using MapQuest licensed services.
    """
    _endpoint = 'http://www.mapquestapi.com/geocoding/v1/address'

    def _geocode(self, pq):
        def get_appended_location(location, **kwargs):
            """Add key/value pair to given dict only if value is not empty string."""
            for kw in kwargs:
                if kwargs[kw] != '':
                    location = dict(location, **{kw: kwargs[kw]})
            return location
        location = {}
        location = get_appended_location(location, street=pq.query)
        if location == {}:
            location = get_appended_location(location, street=pq.address)
        location = get_appended_location(location, city=pq.city, county=pq.subregion,
                                         state=pq.state, postalCode=pq.postal, country=pq.country)
        json_ = dict(location=location)
        json_ = json.dumps(json_)
        logger.debug('MQ json: %s', json_)
        query = dict(key=unquote(self._settings['api_key']),
                     json=json_)
        if pq.viewbox is not None:
            query = dict(query, viewbox=pq.viewbox.to_mapquest_str())
        response_obj = self._get_json_obj(self._endpoint, query)
        logger.debug('MQ RESPONSE: %s', response_obj)
        returned_candidates = []  # this will be the list returned
        for r in response_obj['results'][0]['locations']:
            c = Candidate()
            c.locator = r['geocodeQuality']
            c.confidence = r['geocodeQualityCode']  # http://www.mapquestapi.com/geocoding/geocodequality.html
            match_addr_elements = ['street', 'adminArea5', 'adminArea3',
                                   'adminArea2', 'postalCode']  # similar to ESRI
            c.match_addr = ', '.join([r[k] for k in match_addr_elements if k in r])
            c.x = r['latLng']['lng']
            c.y = r['latLng']['lat']
            c.wkid = 4326
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates


class MapQuestSSL(MapQuest):
    _endpoint = 'https://www.mapquestapi.com/geocoding/v1/address'
