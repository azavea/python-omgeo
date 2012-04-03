from base import GeocodeService
from omgeo.places import Candidate
from omgeo.processors.preprocessors import CountryPreProcessor, RequireCountry, ParseSingleLine, ReplaceRangeWithNumber
from omgeo.processors.postprocessors import AttrFilter, AttrExclude, AttrRename, AttrSorter, AttrMigrator, UseHighScoreIfAtLeast, GroupBy, ScoreSorter

class Bing(GeocodeService):
    """
    Class to geocode using Bing services:
     * `Find a Location by Query <http://msdn.microsoft.com/en-us/library/ff701711.aspx>`_
     . * `Find a Location by Address <http://msdn.microsoft.com/en-us/library/ff701714.aspx>`_
    """
    
    ATTR_MAP = {
        'locator':{
            'Rooftop': 'rooftop',
            'Parcel': 'parcel',
            'ParcelCentroid': 'parcel',
            'Interpolation': 'interpolation',
            'InterpolationOffset': 'interpolation_offset',
        }
    }

    _endpoint = 'http://dev.virtualearth.net/REST/v1/Locations'

    _settings = {'inclnb': 1, 'rejected_entities': ['AdminDivision1', 'AdminDivision2', 'AdminDivision3', 'CountryRegion', 'DisputedArea', 'MountainRange', 'Ocean', 'Peninsula', 'Planet', 'Plate', 'Postcode', 'Postcode1', 'Postcode2', 'Postcode3', 'Postcode4', 'Sea']}

    _preprocessors = []
    """Preprocessors to use with this geocoder service, in order of desired execution."""
    _preprocessors.append(ReplaceRangeWithNumber()) # 766-68 Any St. -> 766 Any St. 
    
    _postprocessors = []
    """Postprocessors to use with this geocoder service, in order of desired execution."""
    _postprocessors.append(AttrExclude(_settings['rejected_entities'], 'entity'))
    _postprocessors.append(AttrRename('locator', ATTR_MAP['locator']))
    _postprocessors.append(AttrSorter(['rooftop', 'parcel', 'interpolation_offset', 'interpolation'], 'locator'))
    _postprocessors.append(AttrSorter(['Address'], 'entity')) # Address first, then the rest
    _postprocessors.append(AttrMigrator('confidence', 'score', {'High':100, 'Medium':85, 'Low':50}))
    _postprocessors.append(ScoreSorter())
    _postprocessors.append(GroupBy('match_addr'))
    
    # TODO: make scores
    """
    Settings used by the Bing GeocodeService object may include:
    ============================================================
    api_key --  The API key used to access Bing services.
    inclnb  --  One of the following values:
                 * 0: Do not include neighborhood information.
                 * 1: Include neighborhood information when available.
    """
    def _geocode(self, pq):
        if pq.query.strip() == '':
            # No single line query string; use address elements:
            query = {
                'addressLine':pq.address,
                'locality':pq.city,
                'adminDistrict':pq.state,
                'postalCode':pq.postal,
                'countryRegion':pq.country}
        else:
            query = {
                'query':pq.query}
        
        if pq.viewbox is not None:
            query = dict(query, **{'umv':pq.viewbox.to_bing_str()})

        if hasattr(pq, 'culture'): query = dict(query, c=pq.culture)
        if hasattr(pq, 'user_ip'): query = dict(query, uip=pq.user_ip)
        if hasattr(pq, 'user_lat') and hasattr(pq, 'user_lon'):
            query = dict(query, **{'ul':'%f,%f' % (pq.user_lat, pq.user_lon)})

        addl_settings = {
                'inclnb':self._settings['inclnb'],
                'key':self._settings['api_key']}
        query = dict(query, **addl_settings)
        
        response_obj = self._get_json_obj(self._endpoint, query)
        if response_obj is False: return []
  
        wkid = 4326
        
        returned_candidates = [] # this will be the list returned
        for r in response_obj['resourceSets'][0]['resources']:    
            c = Candidate()
            c.entity = r['entityType']
            c.locator = r['geocodePoints'][0]['calculationMethod'] # ex. "Parcel"
            c.confidence = r['confidence'] # High|Medium|Low
            c.match_addr = r['name'] # ex. "1 Microsoft Way, Redmond, WA 98052"
            c.x = r['geocodePoints'][0]['coordinates'][1] # long, ex. -122.13
            c.y = r['geocodePoints'][0]['coordinates'][0] # lat, ex. 47.64
            c.wkid = wkid
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates

class EsriGeocodeService(GeocodeService):
    """
    Settings used by an EsriGeocodeService object may include:
    ============================================================
    api_key --  The API key used to access ESRI premium services.  If this
                key is present, the object's endpoint will be set to use
                premium tasks.
    """

    def __init__(self, preprocessors=None, postprocessors=None, settings={}):
        """
        ESRI services can be used as free services or "premium tasks".  If an
        ESRI service is created with an api_key in the settings, we'll set this
        service up with the premium task URL.
        """
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

        service_url = 'http://tasks.arcgisonline.com/ArcGIS'
        
        if 'api_key' in self._settings:
            service_url = 'http://premiumtasks.arcgisonline.com/server'

        self._endpoint = service_url + self._task_endpoint

    def append_token_if_needed(self, query_dict):
        if 'api_key' in self._settings:
            query_dict.update({'token': self._settings['api_key']})
        return query_dict

class EsriEU(EsriGeocodeService):
    """
    Class to geocode using the ESRI TA_Address_EU locator service.

    As of 29 Dec 2011, the ESRI website claims to support Andorra, Austria, 
    Belgium, Denmark, Finland, France, Germany, Gibraltar, Ireland, Italy,
    Liechtenstein, Luxembourg, Monaco, The Netherlands, Norway, Portugal,
    San Marino, Spain, Sweden, Switzerland, United Kingdom, and Vatican City.
    """
    ATTR_MAP = {
        'locator':{
            'EU_Street_Addr': 'interpolation',
        },
    }

    _wkid = 4326

    _supported_countries_fips = ['AN', 'AU', 'BE', 'DA', 'FI', 'FR', 'GM', 'GI', 'EI', 
        'IT', 'LS', 'LU', 'MN', 'NL', 'NO', 'PO', 'SM', 'SP', 'SW', 'SZ', 'UK', 'VT']
    """FIPS codes of supported countries"""

    _supported_countries_iso2 = ['AD', 'AT', 'BE', 'DK', 'FI', 'FR', 'DE', 'GI', 'IE', 
        'IT', 'LI', 'LU', 'MC', 'NL', 'NO', 'PT', 'SM', 'ES', 'SE', 'CH', 'GB', 'VC']
    """ISO-2 codes of supported countries"""

    _map_fips_to_iso2 = {
        'AN':'AD',
        'AU':'AT',
        'DA':'DK',
        'GM':'DE',
        'EI':'IE',
        'LS':'LI',
        'MN':'MC',
        'PO':'PT',
        'SP':'ES',
        'SW':'SE',
        'SZ':'CH',
        'UK':'GB',
        'VT':'VC',
        }
    """Map of FIPS to ISO-2 codes, if they are different."""

    _preprocessors = []
    """Preprocessors to use with this geocoder service, in order of desired execution."""
    # Valid inputs for the ESRI EU geocoder are ISO alpha-2 or -3 country codes.
    _preprocessors.append(CountryPreProcessor(_supported_countries_iso2, _map_fips_to_iso2))
    _preprocessors.append(ParseSingleLine())
    _preprocessors.append(RequireCountry('GB'))
    
    _postprocessors = []
    """Postprocessors to use with this geocoder service, in order of desired execution."""
    _postprocessors.append(AttrFilter(['EU_Street_Addr'], 'locator', False))
    _postprocessors.append(AttrRename('locator', ATTR_MAP['locator']))
    _postprocessors.append(UseHighScoreIfAtLeast(100))
    _postprocessors.append(GroupBy('match_addr'))
    _postprocessors.append(ScoreSorter())

    _task_endpoint = '/rest/services/Locators/TA_Address_EU/GeocodeServer/findAddressCandidates'
            
    def _geocode(self, location):
        query = {
            'Address':location.address,
            'City':location.city,
            'Postcode':location.postal,
            'Country':location.country,
            'outfields':'Loc_name',
            'f':'json'}

        query = self.append_token_if_needed(query)

        response_obj = self._get_json_obj(self._endpoint, query)
        if response_obj is False: return []
        
        returned_candidates = [] # this will be the list returned
        try:
            for rc in response_obj['candidates']: 
                c = Candidate()
                c.locator = rc['attributes']['Loc_name']
                c.score = rc['score']
                c.match_addr = rc['address']
                c.x = rc['location']['x']
                c.y = rc['location']['y']
                c.wkid = self._wkid
                c.geoservice = self.__class__.__name__
                returned_candidates.append(c)
        except KeyError as ex:
            print "I'm not what you expected, but hey, I'm still JSON! %s" % ex #TODO: put on error stack
            return []
        return returned_candidates

class EsriNA(EsriGeocodeService):
    """
    Class to geocode using the ESRI TA_Address_NA_10 locator service.
    """

    ATTR_MAP = {
        'locator':{
            'RoofTop': 'rooftop',
            'Streets': 'interpolation',
        },
    }

    _preprocessors = []
    """Preprocessors to use with this geocoder service, in order of desired execution."""
    _preprocessors.append(CountryPreProcessor(['US', 'CA']))
    
    _postprocessors = []
    """Postprocessors to use with this geocoder service, in order of desired execution."""
    _postprocessors.append(AttrRename('locator', ATTR_MAP['locator']))
    _postprocessors.append(AttrFilter(['rooftop', 'interpolation'], 'locator'))
    _postprocessors.append(AttrSorter(['rooftop', 'interpolation'], 'locator'))
    _postprocessors.append(UseHighScoreIfAtLeast(99.8))
    _postprocessors.append(GroupBy('match_addr'))
    _postprocessors.append(ScoreSorter())

    _task_endpoint = '/rest/services/Locators/TA_Address_NA_10/GeocodeServer/findAddressCandidates'
            
    def _geocode(self, location):
        query = {
            'SingleLine':location.query,
            'Address':location.address,
            'City':location.city,
            'State':location.state,
            'Zip':location.postal,
            'Country':location.country,
            'outfields':'Loc_name,Addr_Type,Zip4_Type',
            'f':'json'}

        query = self.append_token_if_needed(query)

        response_obj = self._get_json_obj(self._endpoint, query)
        if response_obj is False: return [] 

        try:
            wkid = response_obj['spatialReference']['wkid']
        except KeyError:
            pass
        
        returned_candidates = [] # this will be the list returned
        for rc in response_obj['candidates']:         
            try: 
                c = Candidate()
                c.locator = rc['attributes']['Loc_name']
                c.score = rc['score']
                c.match_addr = rc['address']
                c.x = rc['location']['x']
                c.y = rc['location']['y']
                c.wkid = wkid
                c.geoservice = self.__class__.__name__
                returned_candidates.append(c)
            except KeyError:
                pass
        return returned_candidates

class Nominatim(GeocodeService):
    """
    Class to geocode using `Nominatim services <http://open.mapquestapi.com/nominatim/>`_.
    """
    _wkid = 4326

    _endpoint = 'http://open.mapquestapi.com/nominatim/v1/search'

    _settings = {
        'accepted_entities':['building.', 'historic.castle', 'leisure.ice_rink', 'leisure.miniature_golf', 'leisure.sports_centre', 'lesiure.stadium', 'leisure.track', 'lesiure.water_park', 'man_made.lighthouse', 'man_made.works', 'military.barracks', 'military.bunker', 'office.', 'place.house', 'amenity.',  'power.generator', 'railway.station', 'shop.', 'tourism.'],
        'rejected_entities':['amenity.drinking_water', 'amentity.bicycle_parking', 'amentity.ev_charging', 'amentity.grit_bin', 'amentity.atm', 'amentity.hunting_stand', 'amentity.post_box'],
        }

    _preprocessors = []
    """Preprocessors to use with this geocoder service, in order of desired execution."""
    _preprocessors.append(ReplaceRangeWithNumber()) # 766-68 Any St. -> 766 Any St. 
    
    _postprocessors = []
    """Postprocessors to use with this geocoder service, in order of desired execution."""

    _postprocessors.append(AttrFilter(_settings['accepted_entities'], 'entity', exact_match=False))
    _postprocessors.append(AttrExclude(_settings['rejected_entities'], 'entity'))
    
    def _geocode(self, pq):
        query = {
            'q':pq.query,
            'countrycodes':pq.country, # only takes ISO-2
            'format':'json'}
        
        if pq.viewbox is not None:
            query = dict(query, **{'viewbox':pq.viewbox.to_mapquest_str(), 'bounded':pq.bounded})

        response_obj = self._get_json_obj(self._endpoint, query)
        if response_obj is False: return []
  
        returned_candidates = [] # this will be the list returned
        for r in response_obj:    
            c = Candidate()
            c.locator = 'parcel' # we don't have one but this is the closes match
            c.entity = '%s.%s' % (r['class'], r['type']) # ex.: "place.house"
            c.match_addr = r['display_name'] # ex. "Wolf Building, 340, N 12th St, Philadelphia, Philadelphia County, Pennsylvania, 19107, United States of America" #TODO: shorten w/ pieces
            c.x = r['lon'] # long, ex. -122.13
            c.y = r['lat'] # lat, ex. 47.64
            c.wkid = self._wkid
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates

class CitizenAtlas(GeocodeService):
    '''
    Class to geocode using the Washington DC CitizenAtlas <http://citizenatlas.dc.gov/newwebservices>
    '''

    _endpoint = 'http://citizenatlas.dc.gov/newwebservices/locationverifier.asmx/findLocation'

    def _geocode(self, place_query):

        # Define helper functions

        def _get_text_from_nodelist(nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)

        def _create_candidate_from_intersection_element(intersection_element, source_operation):
            c = Candidate()
            c.locator = source_operation
            c.match_addr = _get_text_from_nodelist(
                intersection_element.getElementsByTagName("FULLINTERSECTION")[0].childNodes) + ", WASHINGTON, DC"
            c.y = float(_get_text_from_nodelist(intersection_element.getElementsByTagName("LATITUDE")[0].childNodes))
            c.x = float(_get_text_from_nodelist(intersection_element.getElementsByTagName("LONGITUDE")[0].childNodes))
            confidence_level_elements = intersection_element.getElementsByTagName("ConfidenceLevel")
            c.score = float(_get_text_from_nodelist(confidence_level_elements[0].childNodes))
            c.geoservice = self.__class__.__name__
            return c

        def _create_candidate_from_address_element(match, source_operation):
            if match.getElementsByTagName("FULLADDRESS").length > 0:
                full_address = _get_text_from_nodelist(match.getElementsByTagName("FULLADDRESS")[0].childNodes)
            else:
                full_address = _get_text_from_nodelist(
                    match.getElementsByTagName("STNAME")[0].childNodes) + " " + _get_text_from_nodelist(match.getElementsByTagName("STREET_TYPE")[0].childNodes)
            city = _get_text_from_nodelist(match.getElementsByTagName("CITY")[0].childNodes)
            state = _get_text_from_nodelist(match.getElementsByTagName("STATE")[0].childNodes)
            zipcode = _get_text_from_nodelist(match.getElementsByTagName("ZIPCODE")[0].childNodes)
            c = Candidate()
            c.match_addr = full_address + ", " + city + ", " + state + ", " + zipcode
            confidence_level_elements = match.getElementsByTagName("ConfidenceLevel")
            c.score = float(_get_text_from_nodelist(confidence_level_elements[0].childNodes))
            c.y = float(_get_text_from_nodelist(match.getElementsByTagName("LATITUDE")[0].childNodes))
            c.x = float(_get_text_from_nodelist(match.getElementsByTagName("LONGITUDE")[0].childNodes))
            c.locator = source_operation
            c.geoservice = self.__class__.__name__
            return c

        # Geocode

        query = { 'str': place_query.query }

        response_doc = self._get_xml_doc(self._endpoint, query)
        if response_doc is False: return []

        address_matches = response_doc.getElementsByTagName("Table1")
        if address_matches.length == 0: return []

        if response_doc.getElementsByTagName("sourceOperation").length > 0:
            source_operation = _get_text_from_nodelist(
                response_doc.getElementsByTagName("sourceOperation")[0].childNodes)
        else:
            source_operation = ""

        candidates = [] # this will be the list returned

        for match in address_matches:
            if source_operation == "DC Intersection":
                candidates.append(_create_candidate_from_intersection_element(match, source_operation))
            elif source_operation == "DC Address" or source_operation == "DC Place":
                candidates.append(_create_candidate_from_address_element(match, source_operation))

        return candidates