from base import GeocodeService
import logging
from omgeo.places import Candidate
from omgeo.preprocessors import ReplaceRangeWithNumber
from urlparse import urljoin
from posixpath import join as posixjoin

logger = logging.getLogger(__name__)


class Mapzen(GeocodeService):
    """
    Class to geocode using `Mapzen search service
    <https://mapzen.com/projects/search>`_.

    Settings used by the Mapzen GeocodeService object include:
     * api_key --  The API key used to access search service.

    """
    _wkid = 4326

    # 766-68 Any St. -> 766 Any St.
    DEFAULT_PREPROCESSORS = [ReplaceRangeWithNumber()]
    DEFAULT_POSTPROCESSORS = []

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        if 'api_version' in settings:
            self._api_version = 'v' + str(settings['api_version'])
        else:
            self._api_version = 'v1'

        if 'instance_url' in settings:
            self._base_url = settings['instance_url']
        else:
            self._base_url = 'https://search.mapzen.com'

        self._default_endpoint = urljoin(self._base_url,
                                         posixjoin(self._api_version, 'search'))
        self._key_endpoint = urljoin(self._base_url,
                                     posixjoin(self._api_version, 'place'))
        self._endpoint = self._default_endpoint

        preprocessors = Mapzen.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = Mapzen.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

    def _geocode(self, pq):
        query = {'text': pq.query}

        if pq.country:
            query = dict(query, **{'boundary.country': pq.country})

        if pq.viewbox is not None:
            box = pq.viewbox.to_mapzen_dict()
            query = dict(query, **box)

        if hasattr(pq, 'key'):
            # Swap to the place endpoint and return a single result.
            self._endpoint = self._key_endpoint
            query = {'ids': pq.key}

        if 'api_key' in self._settings:
            query['api_key'] = self._settings['api_key']

        response_obj = self._get_json_obj(self._endpoint, query)
        returned_candidates = []  # this will be the list returned
        features_in_response = response_obj['features']
        for r in features_in_response:
            properties = r['properties']
            geometry = r['geometry']

            score = 100 * float(properties['confidence']) if 'confidence' in properties else 0
            locality = properties['locality'] if 'locality' in properties else ''
            region = properties['region'] if 'region' in properties else ''
            label = properties['label'] if 'label' in properties else ''
            layer = properties['layer'] if 'layer' in properties else ''

            c = Candidate()
            c.locator = layer
            c.match_addr = label
            c.match_region = region
            c.match_city = locality
            c.locator_type = layer
            c.x = float(geometry['coordinates'][0])
            c.y = float(geometry['coordinates'][1])
            c.score = score
            c.wkid = self._wkid
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
