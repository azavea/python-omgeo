import copy
from urllib import urlencode, urlopen
from json import loads

class GeocodeService():
    """
    A tuple of classes representing the geocoders that will be used
    to find addresses for the given locations
    """
    _preprocessors = []
    """
    Preprocessor classes to apply to the given PlaceQuery
    """
    _postprocessors = []
    """
    Postprocessor classes to apply to the list of Candidates obtained
    """
    _settings = {}
    """
    Settings for this geocoder
    """
    _endpoint = ''
    """
    API endpoint URL to use
    """

    def _init_helper(self, preprocessors, postprocessors, settings):
        """
        Overwrite _preprocessors, _postprocessors, and _settings
        if they are set. The default for processors is None, because [] would
        indicate that no pre- or post-processors should be used. Settings
        overwrite default/existing _settings dictionary pairs if they are already set.
        """
        if preprocessors is not None:
            self._preprocessors = preprocessors
        if postprocessors is not None:
            self._postprocessors = postprocessors
        for key in settings:
            self._settings[key] = settings[key]   

    def _settings_checker(self, required_settings=[], accept_none=True):
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
        for keyname in required_settings:
            if keyname not in self._settings:
                return keyname
            if accept_none is False and self._settings[keyname] is None:
                return keyname
        return True
            

    def __init__(self, preprocessors=None, postprocessors=None, settings={}):
        """
        Constructor for GeocodeService objects.
        """
        self._init_helper(preprocessors, postprocessors, settings)

    def _get_json_obj(self, endpoint, query):
        """
        Return False if connection could not be made.
        Otherwise, return a response object from JSON.
        """
        try:
            response = urlopen('%s?%s' % (endpoint, urlencode(query)))
        except:
            raise Exception('Could not connect') #TODO: log this error internally (could not connect, etc)
            return False
        if response.code != 200: return False
        content = response.read()  
        try:  
            return loads(content)
        except ValueError as ex:
            raise Exception('Could not decode JSON: %s' % ex) #TODO: log this error internally 
            return False

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
        
        candidates = self._geocode(processed_pq)

        for p in self._postprocessors: # apply universal candidate postprocessing
            candidates = p.process(candidates) # merge lists

        return candidates
    
    def get_service_name(self):
        return self.__name__
