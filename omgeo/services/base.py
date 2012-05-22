import copy
from datetime import datetime
from json import loads
import logging
import socket
import time
from traceback import format_exc
from urllib import urlencode
from urllib2 import HTTPError, urlopen, URLError
from xml.dom import minidom

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
        Preprocessor classes to apply to the given PlaceQuery, usually
        overwritten in subclass.
        """
        self._postprocessors = []
        """
        Postprocessor classes to apply to the list of Candidates obtained, 
        usually overwritten in subclass.
        """
        self._settings = {}
        """
        Settings for this geocoder, usually overwritten in subclass
        """
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
    
    def _get_response(self, endpoint, query):
        """Returns response or False in event of failure"""
        timeout_secs = self._settings.get('timeout', 10)
        try:
            response = urlopen('%s?%s' % (endpoint, urlencode(query)),
                               timeout=timeout_secs)
        except Exception as ex:
            if type(ex) == socket.timeout:
                logger.info("GEOCODER: %s; EXCEPTION: timed out after %s seconds." % (self.__class__.__name__, timeout_secs))
                return False
            else:
                raise ex
        if response.code != 200:
            raise Exception('Received status code %s for %s. Content is:\n%s'
                            % (self.get_service_name(), response.read()))
        return response
    
    def _get_json_obj(self, endpoint, query):
        """
        Return False if connection could not be made.
        Otherwise, return a response object from JSON.
        """
        response = self._get_response(endpoint, query)
        if response == False:
            return False
        content = response.read()  
        try:  
            return loads(content)
        except ValueError:
            logger.error("GEOCODER: %s; EXCEPTION: couldn't decode JSON: %s" % 
                self.__class__.__name__, content)
            return False

    def _get_xml_doc(self, endpoint, query):
        """
        Return False if connection could not be made.
        Otherwise, return a minidom Document.
        """
        response = self._get_response(endpoint, query)
        if response == False:
            return False
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
        start_time = time.time()
        logger.debug('%s: BEGINNING PREPROCESSING FOR %s' % (time.time() - start_time, self.get_service_name()))
        for p in self._preprocessors:
            processed_pq = p.process(processed_pq)
            logger.debug('%s: Preprocessed through %s' % (time.time() - start_time, p))
            if processed_pq == False: return []
        try:
            start = datetime.now()
            candidates = self._geocode(processed_pq)
            end = datetime.now()
            logger.info('GEOCODER: %s; results %d; time %s;' %
                (self.get_service_name(), len(candidates), end-start))
        except:
            logger.info('GEOCODER: %s; EXCEPTION:\n%s' %
                (self.get_service_name(), format_exc()))
            candidates = []
        logger.debug('%s: BEGINNING POSTPROCESSING FOR %s' % (time.time() - start_time, self.get_service_name()))
        for p in self._postprocessors: # apply universal candidate postprocessing
            candidates = p.process(candidates) # merge lists
            logger.debug('%s: Postprocessed through %s' % (time.time() - start_time, p))

        return candidates
    
    def get_service_name(self):
        return self.__class__.__name__
