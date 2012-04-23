import copy
from urllib import urlencode, urlopen
from json import loads
from xml.dom import minidom
from datetime import datetime
from traceback import format_exc
import logging

logger = logging.getLogger(__name__)

class GeocodeService():
    """
    A tuple of classes representing the geocoders that will be used
    to find addresses for the given locations
    """

    _endpoint = ''
    """
    API endpoint URL to use
    """

    def __init__(self, preprocessors=None, postprocessors=None,
            settings=None):
        """
        Overwrite _preprocessors, _postprocessors, and _settings
        if they are set.
        """

        self._preprocessors = []
        """
        Preprocessor classes to apply to the given PlaceQuery
        """
        self._postprocessors = []
        """
        Postprocessor classes to apply to the list of Candidates obtained
        """
        self._settings = {}
        """
        Settings for this geocoder
        """
        # self._endpoint = ''
        if preprocessors is not None:
            self._preprocessors = preprocessors
        if postprocessors is not None:
            self._postprocessors = postprocessors
        if settings is not None:
            for key in settings:
                self._settings[key] = settings[key]   

    def _settings_checker(self, required_settings=None, accept_none=True):
        """
        Take a list of required _settings dictionary keys
        and make sure they are set. This can be added to a custom
        constructor in a subclass and tested to see if it returns ``True``.

        Arguments:
        ==========
        required_settings   -- A list of required keys to look for.
        accept_none         -- Boolean set to True if None is an acceptable
                               setting. Set to False if None is not an
                               acceptable setting.

        Return values:
        ==============
         * bool ``True`` if all required settings exist, OR
         * str ``keyname`` for the first key that is not found in _settings.
        """
        if required_settings is not None:
            for keyname in required_settings:
                if keyname not in self._settings:
                    return keyname
                if accept_none is False and self._settings[keyname] is None:
                    return keyname
        return True
            
    def _get_json_obj(self, endpoint, query):
        """
        Return False if connection could not be made.
        Otherwise, return a response object from JSON.
        """
        try:
            response = urlopen('%s?%s' % (endpoint, urlencode(query)))
        except:
            logger.error("%s couldn't connect to server" %
                self.get_service_name())
            logger.error(format_exc())
            return False
        if response.code != 200: return False
        content = response.read()  
        try:  
            return loads(content)
        except ValueError:
            logger.error("%s couldn't decode JSON: %s" % 
                self.get_service_name, content)
            logger.error(format_exc())
            return False

    def _get_xml_doc(self, endpoint, query):
        """
        Return False if connection could not be made.
        Otherwise, return a minidom Document.
        """
        try:
            response = urlopen('%s?%s' % (endpoint, urlencode(query)))
        except:
            logger.error("%s couldn't connect to server" %
                self.get_service_name())
            logger.error(format_exc())
            return False
        if response.code != 200: return False
        return minidom.parse(response)

    def _geocode(self, place_query):
        """
        Given a (preprocessed) PlaceQuery object,
        return a list of of Candidate objects.
        """
        raise NotImplementedError(
            'GeocodeService subclasses must implement _geocode().')

    def geocode(self, pq):
        """
        Given an unprocessed PlaceQuery object, return a post-processed
        list of Candidate objects.
        """
        processed_pq = copy.copy(pq)

        for p in self._preprocessors:
            processed_pq = p.process(processed_pq)
            if processed_pq == False: return []
        
    
        try:
            start = datetime.now()
            candidates = self._geocode(processed_pq)
            end = datetime.now()
            logger.info('GEOCODER: %s; results %d; time %s;' %
                (self.__class__.__name__, len(candidates), end-start))
        except:
            logger.info('GEOCODER: %s; Exception when attempting to geocode %s' %
                (self.__class__.__name__, format_exc()))
            candidates = []

        for p in self._postprocessors: # apply universal candidate postprocessing
            candidates = p.process(candidates) # merge lists

        return candidates
    
    def get_service_name(self):
        return self.__class__.__name__
