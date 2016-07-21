from base import GeocodeService
import logging
from omgeo.places import Candidate
from omgeo.preprocessors import ReplaceRangeWithNumber
from omgeo.postprocessors import (AttrFilter, AttrRename, AttrSorter, AttrMigrator,
                                  UseHighScoreIfAtLeast, GroupBy, ScoreSorter)

logger = logging.getLogger(__name__)


class Bing(GeocodeService):
    """
    Class to geocode using Bing services:
     * `Find a Location by Query <http://msdn.microsoft.com/en-us/library/ff701711.aspx>`_
     * `Find a Location by Address <http://msdn.microsoft.com/en-us/library/ff701714.aspx>`_

    Settings used by the Bing GeocodeService object may include:
     * api_key --  The API key used to access Bing services.

    """
    _endpoint = 'http://dev.virtualearth.net/REST/v1/Locations'

    DEFAULT_PREPROCESSORS = [
        ReplaceRangeWithNumber()
    ]

    DEFAULT_POSTPROCESSORS = [
        AttrMigrator('confidence', 'score',
                     {'High': 100, 'Medium': 85, 'Low': 50}),
        UseHighScoreIfAtLeast(100),
        AttrFilter(['Address', 'AdministrativeBuilding',
                    'AgriculturalStructure',
                    'BusinessName', 'BusinessStructure',
                    'BusStation', 'Camp', 'Church', 'CityHall',
                    'CommunityCenter', 'ConventionCenter',
                    'Courthouse', 'Factory', 'FerryTerminal',
                    'FishHatchery', 'Fort', 'Garden', 'Geyser',
                    'Heliport', 'IndustrialStructure',
                    'InformationCenter', 'Junction',
                    'LandmarkBuilding', 'Library', 'Lighthouse',
                    'Marina', 'MedicalStructure', 'MetroStation',
                    'Mine', 'Mission', 'Monument', 'Mosque',
                    'Museum', 'NauticalStructure', 'NavigationalStructure',
                    'OfficeBuilding', 'ParkAndRide', 'PlayingField',
                    'PoliceStation', 'PostOffice', 'PowerStation',
                    'Prison', 'RaceTrack', 'ReligiousStructure',
                    'RestArea', 'Ruin', 'ShoppingCenter', 'Site',
                    'SkiArea', 'Spring', 'Stadium', 'Temple',
                    'TouristStructure'], 'entity'),
        AttrRename('locator', dict(Rooftop='rooftop',
                                   Parcel='parcel',
                                   ParcelCentroid='parcel',
                                   Interpolation='interpolation',
                                   InterpolationOffset='interpolation_offset')),
        AttrSorter(['rooftop', 'parcel',
                    'interpolation_offset', 'interpolation'],
                   'locator'),
        AttrSorter(['Address'], 'entity'),
        ScoreSorter(),
        GroupBy(('x', 'y')),
        GroupBy('match_addr')]
    DEFAULT_POSTPROCESSORS = []

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = Bing.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = Bing.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

    def _geocode(self, pq):
        if pq.query.strip() == '':
            # No single line query string; use address elements:
            query = {'addressLine': pq.address,
                     'locality': pq.city,
                     'adminDistrict': pq.state,
                     'postalCode': pq.postal,
                     'countryRegion': pq.country}
        else:
            query = {'query': pq.query}

        if pq.viewbox is not None:
            query = dict(query, **{'umv': pq.viewbox.to_bing_str()})
        if hasattr(pq, 'culture'):
            query = dict(query, c=pq.culture)
        if hasattr(pq, 'user_ip'):
            query = dict(query, uip=pq.user_ip)
        if hasattr(pq, 'user_lat') and hasattr(pq, 'user_lon'):
            query = dict(query, **{'ul': '%f,%f' % (pq.user_lat, pq.user_lon)})

        addl_settings = {'key': self._settings['api_key']}
        query = dict(query, **addl_settings)
        response_obj = self._get_json_obj(self._endpoint, query)
        returned_candidates = []  # this will be the list returned
        for r in response_obj['resourceSets'][0]['resources']:
            c = Candidate()
            c.entity = r['entityType']
            c.locator = r['geocodePoints'][0]['calculationMethod']  # ex. "Parcel"
            c.confidence = r['confidence']  # High|Medium|Low
            c.match_addr = r['name']  # ex. "1 Microsoft Way, Redmond, WA 98052"
            c.x = r['geocodePoints'][0]['coordinates'][1]  # long, ex. -122.13
            c.y = r['geocodePoints'][0]['coordinates'][0]  # lat, ex. 47.64
            c.wkid = 4326
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
