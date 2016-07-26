import copy
import logging
from omgeo.places import PlaceQuery
from omgeo.postprocessors import DupePicker, SnapPoints
import time

logger = logging.getLogger(__name__)
stats_logger = logging.getLogger('omgeo.stats')


class Geocoder():
    """
    Class for building a custom geocoder using external APIs.
    """

    DEFAULT_SOURCES = [['omgeo.services.EsriWGS', {}],
                       ['omgeo.services.Nominatim', {}]
                      ]
    DEFAULT_PREPROCESSORS = []
    DEFAULT_POSTPROCESSORS = [
        SnapPoints(),
        DupePicker('match_addr', 'locator',
                   ['rooftop', 'parcel', 'interpolation_offset', 'interpolation'])
    ]

    def _get_service_by_name(self, service_name):
        try:
            module, separator, class_name = service_name.rpartition('.')
            m = __import__(module)
            path = service_name.split('.')[1:]
            for p in path:
                m = getattr(m, p)
            return m
        except Exception as ex:
            raise Exception("%s" % (ex))

    def add_source(self, source):
        """
        Add a geocoding service to this instance.
        """
        geocode_service = self._get_service_by_name(source[0])
        self._sources.append(geocode_service(**source[1]))

    def remove_source(self, source):
        """
        Remove a geocoding service from this instance.
        """
        geocode_service = self._get_service_by_name(source[0])
        self._sources.remove(geocode_service(**source[1]))

    def set_sources(self, sources):
        """
        Creates GeocodeServiceConfigs from each str source
        """
        if len(sources) == 0:
            raise Exception('Must declare at least one source for a geocoder')
        self._sources = []
        for source in sources:  # iterate through a list of sources
            self.add_source(source)

    def __init__(self, sources=None, preprocessors=None, postprocessors=None,
                 waterfall=False):
        """
        :arg list sources: an array of GeocodeServiceConfig() parameters,
                           keyed by module name for the GeocodeService to use, e.g.::

                               [['esri_wgs', {}],
                                ['bing', {'settings': {'request_headers': {'User-Agent': 'Custom User Agent'} },
                                         'preprocessors': [],
                                         'postprocessors': []}],
                                 ...]

        :arg list preprocessors: list of universal preprocessors to use
        :arg list postprocessors: list of universal postprocessors to use
        :arg bool waterfall: sets default for waterfall on geocode() method (default ``False``)
        """

        self._preprocessors = Geocoder.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        self._postprocessors = Geocoder.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        sources = Geocoder.DEFAULT_SOURCES if sources is None else sources
        self.set_sources(sources)
        self.waterfall = waterfall

    def geocode(self, pq, waterfall=None, force_stats_logging=False):
        """
        :arg PlaceQuery pq:  PlaceQuery object (required).
        :arg bool waterfall: Boolean set to True if all geocoders listed should
                             be used to find results, instead of stopping after
                             the first geocoding service with valid candidates
                             (defaults to self.waterfall).
        :arg bool force_stats_logging: Raise exception if stats logging fails (default False).
        :returns: Returns a dictionary including:
                   * candidates - list of Candidate objects
                   * upstream_response_info - list of UpstreamResponseInfo objects
        """

        start_time = time.time()
        waterfall = self.waterfall if waterfall is None else waterfall
        if type(pq) in (str, unicode):
            pq = PlaceQuery(pq)
        processed_pq = copy.copy(pq)

        for p in self._preprocessors:  # apply universal address preprocessing
            processed_pq = p.process(processed_pq)
            if not processed_pq:
                return get_result()  # universal preprocessor rejects PlaceQuery

        upstream_response_info_list = []
        processed_candidates = []
        for gs in self._sources:  # iterate through each GeocodeService
            candidates, upstream_response_info = gs.geocode(processed_pq)
            if upstream_response_info is not None:
                upstream_response_info_list.append(upstream_response_info)
            processed_candidates += candidates  # merge lists
            if waterfall is False and len(processed_candidates) > 0:
                break  # if >= 1 good candidate, don't go to next geocoder

        for p in self._postprocessors:  # apply univ. candidate postprocessing
            if processed_candidates == []:
                break  # avoid post-processing empty list
            processed_candidates = p.process(processed_candidates)

        result = dict(candidates=processed_candidates,
                      upstream_response_info=upstream_response_info_list)
        stats_dict = self.convert_geocode_result_to_nested_dicts(result)
        stats_dict = dict(stats_dict, original_pq=pq.__dict__)
        try:
            stats_logger.info(stats_dict)
        except Exception as exception:
            logger.error('Encountered exception while logging stats %s:\n%s', stats_dict, exception)
            if force_stats_logging:
                raise exception
        return result

    def get_candidates(self, pq, waterfall=None):
        """
        Geocode and return just the list of Candidate objects.
        """
        return self.geocode(pq, waterfall)['candidates']

    def convert_geocode_result_to_nested_dicts(self, result):
        def get_uri_dict(uri_item):
            uri_dict = copy.copy(uri_item).__dict__
            uri_dict['processed_pq'] = uri_dict['processed_pq'].__dict__
            return uri_dict
        uri_set = [get_uri_dict(uri_item) for uri_item in result['upstream_response_info']]
        return dict(candidates=[candidate.__dict__ for candidate in result['candidates']],
                    upstream_response_info=uri_set)
