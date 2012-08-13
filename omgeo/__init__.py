import copy
import logging
from omgeo.places import PlaceQuery
from omgeo.processors.postprocessors import DupePicker, SnapPoints
import time

stats_logger = logging.getLogger('omgeo.stats')

class Geocoder():
    """
    17h11
    The base geocode class.  This class can be initialized with settings
    for each geocoder and/or settings for the geocoder itself.

    Arguments:
    ==========
    sources         -- a dictionary of GeocodeServiceConfig() parameters,
                       keyed by module name for the GeocodeService to use
                       ex: {'esri_na':{}, 
                            'bing': {'settings': {},
                                     'preprocessors': [],
                                     'postprocessors': []},
                            ...}
    preprocessors   -- list of universal preprocessors to use
    postprocessors  -- list of universal postprocessors to use
    waterfall       -- sets default for waterfall on geocode() method
                       (default False)
    """

    DEFAULT_SOURCES = [['omgeo.services.EsriNA', {}],
                       ['omgeo.services.EsriEU', {}],
                       ['omgeo.services.Nominatim', {}]]
    DEFAULT_PREPROCESSORS = []
    DEFAULT_POSTPROCESSORS = [SnapPoints(),
                              DupePicker('match_addr', 'locator',
                                         ['rooftop',
                                          'parcel',
                                          'interpolation_offset',
                                          'interpolation'])]
    
    def _get_service_by_name(self, service_name):
        try:
            module, separator, class_name = service_name.rpartition('.')
            m = __import__( module )
            path = service_name.split('.')[1:]
            for p in path:
                m = getattr(m, p)
            return m
        except Exception as ex:
            raise Exception("%s" % (ex))

    def add_source(self, source):
        geocode_service = self._get_service_by_name(source[0])
        self._sources.append(geocode_service(**source[1]))

    def remove_source(self, source):
        geocode_service = self._get_service_by_name(source[0])
        self._sources.remove(geocode_service(**source[1]))        

    def set_sources(self, sources):
        """
        Creates GeocodeServiceConfigs from each str source
        
        Argument:
        =========
        sources --  list of source-settings pairs
                    ex. "[['EsriNA', {}], ['Nominatim', {}]]"
        """
        if len(sources) == 0:
            raise Exception('Must declare at least one source for a geocoder')
        self._sources = []
        for source in sources: # iterate through a list of sources
            self.add_source(source)

    def __init__(self, sources=None, preprocessors=None, postprocessors=None,
                 waterfall=False):
        self._preprocessors = Geocoder.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        self._postprocessors = Geocoder.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        sources = Geocoder.DEFAULT_SOURCES if sources is None else sources
        self.set_sources(sources)
        self.waterfall = waterfall
        
    def geocode(self, pq, waterfall=None):
        """
        Returns a dictionary including:
         * candidates - list of Candidate objects
         * upstream_response_info - list of UpstreamResponseInfo objects

        Arguments:
        ==========
        pq          --  A PlaceQuery object (required).
        waterfall   --  Boolean set to True if all geocoders listed should
                        be used to find results, instead of stopping after
                        the first geocoding service with valid candidates
                        (defaults to <Geocoder instance>.waterfall).
        """          
        start_time = time.time()
        waterfall = self.waterfall if waterfall is None else waterfall
        if type(pq) in (str, unicode):
            pq = PlaceQuery(pq)
        processed_pq = copy.copy(pq)
        
        for p in self._preprocessors: # apply universal address preprocessing
            processed_pq = p.process(processed_pq)
            if processed_pq == False:
                return get_result() # universal preprocessor rejects PlaceQuery
            
        upstream_response_info_list = []
        processed_candidates = []
        for gs in self._sources: # iterate through each GeocodeService
            candidates, upstream_response_info = gs.geocode(processed_pq)
            if upstream_response_info is not None:
                upstream_response_info_list.append(upstream_response_info)
            processed_candidates += candidates # merge lists
            if waterfall is False and len(processed_candidates) > 0:
                break # if >= 1 good candidate, don't go to next geocoder

        for p in self._postprocessors: # apply univ. candidate postprocessing
            if processed_candidates == []:
                break; # avoid post-processing empty list
            processed_candidates = p.process(processed_candidates)
            
        result = dict(candidates=processed_candidates,
                      upstream_response_info=upstream_response_info_list)
        stats_logger.info(self.convert_geocode_result_to_nested_dicts(result))
        return result
    
    def get_candidates(self, pq, waterfall=None):
        return self.geocode(pq, waterfall)['candidates']
    
    def convert_geocode_result_to_nested_dicts(self, result):
        def get_uri_dict(uri_item):
            uri_dict = copy.copy(uri_item).__dict__
            uri_dict['processed_pq'] = uri_dict['processed_pq'].__dict__
            return uri_dict
        uri_set = [get_uri_dict(uri_item) for uri_item in result['upstream_response_info']]
        return dict(candidates=[candidate.__dict__ for candidate in result['candidates']],
                    upstream_response_info=uri_set)
        