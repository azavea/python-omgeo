from base import GeocodeService
from omgeo.places import Candidate
from omgeo.processors.preprocessors import CountryPreProcessor, RequireCountry, ParseSingleLine, ReplaceRangeWithNumber
from omgeo.processors.postprocessors import AttrFilter, AttrExclude, AttrRename, AttrSorter, AttrMigrator, UseHighScoreIfAtLeast, GroupBy, ScoreSorter

from suds.client import Client

import logging

logger = logging.getLogger(__name__)

class Bing(GeocodeService):
    """
    Class to geocode using Bing services:
     * `Find a Location by Query <http://msdn.microsoft.com/en-us/library/ff701711.aspx>`_
     . * `Find a Location by Address <http://msdn.microsoft.com/en-us/library/ff701714.aspx>`_

    Settings used by the Bing GeocodeService object may include:
    ============================================================
    api_key --  The API key used to access Bing services.
    """

    _endpoint = 'http://dev.virtualearth.net/REST/v1/Locations'
    
    LOCATOR_MAP = {
        'Rooftop': 'rooftop',
        'Parcel': 'parcel',
        'ParcelCentroid': 'parcel',
        'Interpolation': 'interpolation',
        'InterpolationOffset': 'interpolation_offset',
    }

    DEFAULT_REJECTS = ['AdminDivision1', 'AdminDivision2', 'AdminDivision3', 'CountryRegion', 'DisputedArea', 'MountainRange', 'Ocean', 'Peninsula', 'Planet', 'Plate', 'Postcode', 'Postcode1', 'Postcode2', 'Postcode3', 'Postcode4', 'Sea']

    DEFAULT_PREPROCESSORS = [
        ReplaceRangeWithNumber()
    ]
    
    DEFAULT_POSTPROCESSORS = [
        AttrExclude(DEFAULT_REJECTS, 'entity'),
        AttrRename('locator', LOCATOR_MAP),
        AttrSorter(['rooftop', 'parcel', 'interpolation_offset', 'interpolation'], 'locator'),
        AttrSorter(['Address'], 'entity'),
        AttrMigrator('confidence', 'score', {'High':100, 'Medium':85, 'Low':50}),
        ScoreSorter(),
        GroupBy('match_addr')
    ]
    
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):

        preprocessors = Bing.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = Bing.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors

        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

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

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
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

class EsriSoapGeocodeService(EsriGeocodeService):
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        # First, initialize the usual geocoder stuff like settings and
        # processors
        EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)
        
        # Our suds client
        self._client = None

        # The CandidateFields returned by an ESRI geocoder. The result rows are
        # ordered just as they are - there are no 'keys' in the results
        self._fields = None

        # Used to map the returned results' fields to a Candidate's fields
        self._mapping = {}

        # Set up the URLs necessary to get soap and create a suds clients
        if 'api_key' in self._settings:
            self._endpoint = self._endpoint + "?token=" + self._settings['api_key']
            self._client = Client(self._endpoint + '&wsdl')
            # WSDL's url doesn't set your token so we have to do that, too.
            self._client.set_options(location=self._endpoint)
        else:
            self._client = Client(self._endpoint + '?wsdl')

        # Grab the candidate fields for later - we'll use them in every call
        self.fields = self._client.service.GetCandidateFields()

    def _get_property_set_properties(self, location_dict):
        props = []
        for k, v in location_dict.iteritems():
            ps = self._client.factory.create('PropertySetProperty')
            ps.Key = k
            ps.Value = v
            props.append(ps)
        return props

    
    def _get_candidates_from_record_set(self, record_set):
        """
        Given a RecordSet, create a list of Candidate objects for processing
        """
        candidates = []
        for record in record_set.Records.Record:
            
            c_dict = {}

            for field, value in zip(record_set.Fields.FieldArray.Field,
                        record.Values.Value):
                    
                if field.Name in self._mapping:
                    c_dict[self._mapping[field.Name]] = value
                
            candidate = Candidate(**c_dict)
            candidate.wkid = self._wkid
            candidate.geoservice = self.__class__.__name__
            candidates.append(candidate)
        return candidates

class EsriEUGeocodeService():
    """
    Defaults for Esri EU Geocoders

    As of 29 Dec 2011, the ESRI website claims to support Andorra, Austria, 
    Belgium, Denmark, Finland, France, Germany, Gibraltar, Ireland, Italy,
    Liechtenstein, Luxembourg, Monaco, The Netherlands, Norway, Portugal,
    San Marino, Spain, Sweden, Switzerland, United Kingdom, and Vatican City.
    """
    _wkid = 4326

    _SUPPORTED_COUNTRIES_FIPS = ['AN', 'AU', 'BE', 'DA', 'FI', 'FR', 'GM', 'GI', 'EI', 
        'IT', 'LS', 'LU', 'MN', 'NL', 'NO', 'PO', 'SM', 'SP', 'SW', 'SZ', 'UK', 'VT']
    """FIPS codes of supported countries"""

    _SUPPORTED_COUNTRIES_ISO2 = ['AD', 'AT', 'BE', 'DK', 'FI', 'FR', 'DE', 'GI', 'IE', 
        'IT', 'LI', 'LU', 'MC', 'NL', 'NO', 'PT', 'SM', 'ES', 'SE', 'CH', 'GB', 'VC']
    """ISO-2 codes of supported countries"""

    _MAP_FIPS_TO_ISO2 = {
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

    LOCATOR_MAP = {
        'EU_Street_Addr': 'interpolation',
    }

    DEFAULT_PREPROCESSORS = [
        CountryPreProcessor(
            _SUPPORTED_COUNTRIES_ISO2,
            _MAP_FIPS_TO_ISO2),
        ParseSingleLine(),
        RequireCountry('GB'),
    ]
        
    DEFAULT_POSTPROCESSORS = [
        AttrFilter(['EU_Street_Addr'], 'locator', False),
        AttrRename('locator', LOCATOR_MAP),
        UseHighScoreIfAtLeast(100),
        GroupBy('match_addr'),
        ScoreSorter(),
    ]

class EsriEUSoap(EsriSoapGeocodeService, EsriEUGeocodeService):
    _task_endpoint = '/services/Locators/TA_Address_EU/GeocodeServer'

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = EsriEUGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = EsriEUGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors

        EsriSoapGeocodeService.__init__(self, preprocessors, postprocessors, settings)
        
        self._mapping = {
            'Loc_name': 'locator',
            'Match_addr': 'match_addr',
            'Score': 'score',
            'X': 'x',
            'Y': 'y',
        }

    def _geocode(self, location):
        address = self._client.factory.create('PropertySet')

        # Split address
        location_dict = {
            'Address': location.address,
            'City': location.city,
            'Postcode': location.postal,
            'Country': location.country
        }

        address.PropertyArray.PropertySetProperty.append(
                self._get_property_set_properties(location_dict))

        result_set = self._client.service.FindAddressCandidates(Address=address)

        try:
            candidates = self._get_candidates_from_record_set(result_set)
        except AttributeError:
            if result_set.Records == "":
                return []

        return candidates

class EsriEU(EsriGeocodeService, EsriEUGeocodeService):
    _task_endpoint = '/rest/services/Locators/TA_Address_EU/GeocodeServer/findAddressCandidates'
            
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = EsriEUGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = EsriEUGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors

        EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)

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
            logger.warning('Received unusual JSON result from geocode: %s, %s' %
                (response_obj, ex))
            return []
        return returned_candidates

class EsriNAGeocodeService():
    """
    Defaults for the EsriNAGeocodeService
    """

    LOCATOR_MAP = {
        'RoofTop': 'rooftop',
        'Streets': 'interpolation',
    }

    DEFAULT_PREPROCESSORS = [
        CountryPreProcessor(['US', 'CA'])
    ]

    DEFAULT_POSTPROCESSORS = [
        AttrRename('locator', LOCATOR_MAP),
        AttrFilter(['rooftop', 'interpolation'], 'locator'),
        AttrSorter(['rooftop', 'interpolation'], 'locator'),
        UseHighScoreIfAtLeast(99.8),
        GroupBy('match_addr'),
        ScoreSorter(),
    ]

class EsriNASoap(EsriSoapGeocodeService, EsriNAGeocodeService):
    """
    Use the SOAP version of the ArcGIS-10-style Geocoder for North America
    """
    _task_endpoint = '/services/Locators/TA_Address_NA_10/GeocodeServer'
    _wkid = 4326
    
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = EsriNAGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = EsriNAGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        
        EsriSoapGeocodeService.__init__(self, preprocessors, postprocessors, settings)

        self._mapping = {
            'Loc_name': 'locator',
            'Match_addr': 'match_addr',
            'Score': 'score', 'X': 'x',
            'Y': 'y',
        }

    def _geocode(self, location):
        address = self._client.factory.create('PropertySet')

        if location.query:
            # Single line geocoding
            location_dict = {
                'Single Line Input': location.query
            }
        else:
            # Split address
            location_dict = {
                'Address': location.address,
                'City': location.city,
                'Country': location.country,
                'Zip': location.postal
            }

            # Check for full postal codes
            if location.country.lower == 'us' and len(location.postal > 9):
                location_dict['Zip'] = location.postal[:5]
                location_dict['Zip4'] = location.postal[-4:]

        address.PropertyArray.PropertySetProperty.append(
                self._get_property_set_properties(location_dict))

        result_set = self._client.service.FindAddressCandidates(Address=address)

        try:
            candidates = self._get_candidates_from_record_set(result_set)
        except AttributeError:
            if result_set.Records == "":
                return []

        return candidates
        
        
class EsriNA(EsriGeocodeService, EsriNAGeocodeService):
    _task_endpoint = '/rest/services/Locators/TA_Address_NA_10/GeocodeServer/findAddressCandidates'
            
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = EsriNAGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = EsriNAGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        
        EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)


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

    DEFAULT_ACCEPTED_ENTITIES = ['building.', 'historic.castle', 'leisure.ice_rink', 'leisure.miniature_golf', 'leisure.sports_centre', 'lesiure.stadium', 'leisure.track', 'lesiure.water_park', 'man_made.lighthouse', 'man_made.works', 'military.barracks', 'military.bunker', 'office.', 'place.house', 'amenity.',  'power.generator', 'railway.station', 'shop.', 'tourism.']

    DEFAULT_REJECTED_ENTITIES = ['amenity.drinking_water',
'amentity.bicycle_parking', 'amentity.ev_charging', 'amentity.grit_bin',
'amentity.atm', 'amentity.hunting_stand', 'amentity.post_box']

    """Preprocessors to use with this geocoder service, in order of desired execution."""
    DEFAULT_PREPROCESSORS=ReplaceRangeWithNumber() # 766-68 Any St. -> 766 Any St. 
    
    """Postprocessors to use with this geocoder service, in order of desired execution."""

    DEFAULT_POSTPROCESSORS = [
        AttrFilter(DEFAULT_ACCEPTED_ENTITIES, 'entity', exact_match=False),
        AttrExclude(DEFAULT_REJECTED_ENTITIES, 'entity')
    ]
    
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = Bing.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = Bing.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

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
