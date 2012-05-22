import copy
import logging
from omgeo.places import PlaceQuery
from omgeo.processors.postprocessors import DupePicker, SnapPoints
import time
import timeout

logger = logging.logger = logging.getLogger(__name__)

class Geocoder():
    """
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
    timeout_secs    -- seconds to wait for a geocoding source before moving
                       on to the next one (default 5)
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
        except:
            raise Exception("No geocoder with the name %s" % service_name)

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
                 timeout_secs=5, waterfall=False):
        self._preprocessors = Geocoder.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        self._postprocessors = Geocoder.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        sources = Geocoder.DEFAULT_SOURCES if sources is None else sources
        self.set_sources(sources)
        self.timeout_secs = timeout_secs
        self.waterfall = waterfall
        
    def geocode(self, pq, timeout_secs=None, waterfall=None):
        """
        Returns a list of Candidate objects

        Arguments:
        ==========
        pq          --  A PlaceQuery object (required).
        waterfall   --  Boolean set to True if all geocoders listed should
                        be used to find results, instead of stopping after
                        the first geocoding service with valid candidates
                        (defaults to <Geocoder instance>.waterfall).
        """
        start_time = time.time()
        timeout_secs = self.timeout_secs if timeout_secs is None else timeout_secs
        waterfall = self.waterfall if waterfall is None else waterfall
        if type(pq) in (str, unicode):
            pq = PlaceQuery(pq)
        processed_pq = copy.copy(pq)
        
        for p in self._preprocessors: # apply universal address preprocessing
            processed_pq = p.process(processed_pq)
            if processed_pq == False:
                return []
            
        processed_candidates = []
        for gs in self._sources: # iterate through each GeocodeService
            logger.debug('%s: Geocoding using %s...' % ((time.time() - start_time), gs))
            try:
                candidates = timeout.call_with_timeout(gs.geocode, timeout_secs)(processed_pq)
                processed_candidates += candidates # merge lists
                if waterfall is False and len(processed_candidates) > 0:
                    break # if >= 1 good candidate, don't go to next geocoder
            except timeout.TimeoutException:
                pass # time's up, on to the next one!

        for p in self._postprocessors: # apply univ. candidate postprocessing
            if processed_candidates == []:
                return [] # avoid post-processing empty list
            logger.debug('%s: Applying universal postprocessor %s...' % ((time.time() - start_time), p))
            processed_candidates = p.process(processed_candidates)
            
        return processed_candidates
