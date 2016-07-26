from base import GeocodeService
import logging
from omgeo.places import Candidate
from omgeo.preprocessors import ReplaceRangeWithNumber
from omgeo.postprocessors import AttrFilter, AttrExclude

logger = logging.getLogger(__name__)


class Nominatim(GeocodeService):
    """
    Class to geocode using `Nominatim services hosted
    by MapQuest <http://open.mapquestapi.com/nominatim/>`_.
    """
    _wkid = 4326
    _endpoint = 'http://open.mapquestapi.com/nominatim/v1/search'

    DEFAULT_ACCEPTED_ENTITIES = ['building.', 'historic.castle', 'leisure.ice_rink',
                                 'leisure.miniature_golf',
                                 'leisure.sports_centre', 'lesiure.stadium', 'leisure.track',
                                 'lesiure.water_park', 'man_made.lighthouse', 'man_made.works',
                                 'military.barracks', 'military.bunker', 'office.', 'place.house',
                                 'amenity.',  'power.generator', 'railway.station',
                                 'shop.', 'tourism.']

    DEFAULT_REJECTED_ENTITIES = ['amenity.drinking_water',
                                 'amentity.bicycle_parking', 'amentity.ev_charging',
                                 'amentity.grit_bin', 'amentity.atm',
                                 'amentity.hunting_stand', 'amentity.post_box']

    DEFAULT_PREPROCESSORS = [ReplaceRangeWithNumber()]  # 766-68 Any St. -> 766 Any St.
    """Preprocessors to use with this geocoder service, in order of desired execution."""

    DEFAULT_POSTPROCESSORS = [
        AttrFilter(DEFAULT_ACCEPTED_ENTITIES, 'entity', exact_match=False),
        AttrExclude(DEFAULT_REJECTED_ENTITIES, 'entity')
    ]
    """Postprocessors to use with this geocoder service, in order of desired execution."""

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = Nominatim.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = Nominatim.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

    def _geocode(self, pq):
        query = {'q': pq.query,
                 'countrycodes': pq.country,  # only takes ISO-2
                 'format': 'json'}

        if pq.viewbox is not None:
            query = dict(query, **{'viewbox': pq.viewbox.to_mapquest_str(), 'bounded': pq.bounded})

        response_obj = self._get_json_obj(self._endpoint, query)

        returned_candidates = []  # this will be the list returned
        for r in response_obj:
            c = Candidate()
            c.locator = 'parcel'  # we don't have one but this is the closest match
            c.entity = '%s.%s' % (r['class'], r['type'])  # ex.: "place.house"
            c.match_addr = r['display_name']  # ex. "Wolf Building, 340, N 12th St, Philadelphia, Philadelphia County, Pennsylvania, 19107, United States of America" #TODO: shorten w/ pieces
            c.x = float(r['lon'])  # long, ex. -122.13 # cast to float in 1.3.4
            c.y = float(r['lat'])  # lat, ex. 47.64 # cast to float in 1.3.4
            c.wkid = self._wkid
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
