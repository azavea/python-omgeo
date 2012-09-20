from base import GeocodeService
import json
import logging
from omgeo.places import Candidate
from omgeo.preprocessors import CancelIfPOBox, CountryPreProcessor, RequireCountry, \
    ParseSingleLine, ReplaceRangeWithNumber
from omgeo.postprocessors import AttrFilter, AttrExclude, AttrRename, AttrSorter, \
    AttrMigrator, UseHighScoreIfAtLeast, GroupBy, ScoreSorter
from suds.client import Client
import time
from urllib import unquote

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
                    {'High':100, 'Medium':85, 'Low':50}),
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
            query = {'addressLine':pq.address,
                     'locality':pq.city,
                     'adminDistrict':pq.state,
                     'postalCode':pq.postal,
                     'countryRegion':pq.country}
        else:
            query = {'query':pq.query}
        
        if pq.viewbox is not None:
            query = dict(query, **{'umv':pq.viewbox.to_bing_str()})
        if hasattr(pq, 'culture'): query = dict(query, c=pq.culture)
        if hasattr(pq, 'user_ip'): query = dict(query, uip=pq.user_ip)
        if hasattr(pq, 'user_lat') and hasattr(pq, 'user_lon'):
            query = dict(query, **{'ul':'%f,%f' % (pq.user_lat, pq.user_lon)})

        addl_settings = {'key':self._settings['api_key']}
        query = dict(query, **addl_settings)
        response_obj = self._get_json_obj(self._endpoint, query)
        returned_candidates = [] # this will be the list returned
        for r in response_obj['resourceSets'][0]['resources']:    
            c = Candidate()
            c.entity = r['entityType']
            c.locator = r['geocodePoints'][0]['calculationMethod'] # ex. "Parcel"
            c.confidence = r['confidence'] # High|Medium|Low
            c.match_addr = r['name'] # ex. "1 Microsoft Way, Redmond, WA 98052"
            c.x = r['geocodePoints'][0]['coordinates'][1] # long, ex. -122.13
            c.y = r['geocodePoints'][0]['coordinates'][0] # lat, ex. 47.64
            c.wkid = 4326
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
    
class CitizenAtlas(GeocodeService):
    '''
    Class to geocode using the `Washington DC CitizenAtlas <http://citizenatlas.dc.gov/newwebservices>`_
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

        address_matches = response_doc.getElementsByTagName("Table1")
        if address_matches.length == 0:
            return []

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

class _EsriGeocodeService(GeocodeService):
    """
    Base class for older ESRI geocoders (EsriEU, EsriNA).
    """

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        """
        :arg list preprocessors: preprocessors
        :arg list postprocessors: postprocessors
        :arg dict settings: Settings used by an _EsriGeocodeService object may include
                            the ``api_key`` used to access ESRI premium services.  
                            If this key is present, the object's endpoint will be
                            set to use premium tasks.

        """
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)
        service_url = 'http://premiumtasks.arcgisonline.com/server' if 'api_key' in self._settings \
            else 'http://tasks.arcgisonline.com/ArcGIS'
        self._endpoint = service_url + self._task_endpoint

    def append_token_if_needed(self, query_dict):
        if 'api_key' in self._settings:
            query_dict.update({'token': self._settings['api_key']})
        return query_dict

class _EsriSoapGeocodeService(_EsriGeocodeService):
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        # First, initialize the usual geocoder stuff like settings and
        # processors
        _EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)
        
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

class _EsriEUGeocodeService():
    """
    Base class including for Esri EU REST and SOAP Geocoders

    As of 29 Dec 2011, the ESRI website claims to support Andorra, Austria, 
    Belgium, Denmark, Finland, France, Germany, Gibraltar, Ireland, Italy,
    Liechtenstein, Luxembourg, Monaco, The Netherlands, Norway, Portugal,
    San Marino, Spain, Sweden, Switzerland, United Kingdom, and Vatican City.
    """
    _wkid = 4326

    #: FIPS codes of supported countries
    SUPPORTED_COUNTRIES_FIPS = ['AN', 'AU', 'BE', 'DA', 'FI', 'FR', 'GM', 'GI', 'EI', 
        'IT', 'LS', 'LU', 'MN', 'NL', 'NO', 'PO', 'SM', 'SP', 'SW', 'SZ', 'UK', 'VT']

    #: ISO-2 codes of supported countries
    SUPPORTED_COUNTRIES_ISO2 = ['AD', 'AT', 'BE', 'DK', 'FI', 'FR', 'DE', 'GI', 'IE', 
        'IT', 'LI', 'LU', 'MC', 'NL', 'NO', 'PT', 'SM', 'ES', 'SE', 'CH', 'GB', 'VC']

    #: Map of FIPS to ISO-2 codes, if they are different.
    MAP_FIPS_TO_ISO2 = {
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

    #: Map to standardize locator
    LOCATOR_MAP = {
        'EU_Street_Addr': 'interpolation',
    }

    DEFAULT_PREPROCESSORS = [
        CountryPreProcessor(
            SUPPORTED_COUNTRIES_ISO2,
            MAP_FIPS_TO_ISO2),
        ParseSingleLine(),
    ]
        
    DEFAULT_POSTPROCESSORS = [
        AttrFilter(['EU_Street_Addr'], 'locator', False),
        AttrRename('locator', LOCATOR_MAP),
        UseHighScoreIfAtLeast(100),
        GroupBy('match_addr'),
        ScoreSorter(),
    ]

class _EsriNAGeocodeService():
    """
    Defaults for the _EsriNAGeocodeService
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

class EsriEUSoap(_EsriSoapGeocodeService, _EsriEUGeocodeService):
    _task_endpoint = '/services/Locators/TA_Address_EU/GeocodeServer'

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = _EsriEUGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = _EsriEUGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors

        _EsriSoapGeocodeService.__init__(self, preprocessors, postprocessors, settings)
        
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

class EsriEU(_EsriGeocodeService, _EsriEUGeocodeService):
    _task_endpoint = '/rest/services/Locators/TA_Address_EU/GeocodeServer/findAddressCandidates'
            
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = _EsriEUGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = _EsriEUGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors

        _EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)

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

class EsriNASoap(_EsriSoapGeocodeService, _EsriNAGeocodeService):
    """
    Use the SOAP version of the ArcGIS-10-style Geocoder for North America
    """
    _task_endpoint = '/services/Locators/TA_Address_NA_10/GeocodeServer'
    _wkid = 4326
    
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = _EsriNAGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = _EsriNAGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        
        _EsriSoapGeocodeService.__init__(self, preprocessors, postprocessors, settings)

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
                'SingleLine': location.query
            }
        else:
            # Split address
            location_dict = {
                'Address': location.address,
                'City': location.city,
                'Country': location.country,
                'Zip': location.postal
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
         
class EsriNA(_EsriGeocodeService, _EsriNAGeocodeService):
    """Esri REST Geocoder for North America"""
    _task_endpoint = '/rest/services/Locators/TA_Address_NA_10/GeocodeServer/findAddressCandidates'
            
    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = _EsriNAGeocodeService.DEFAULT_PREPROCESSORS \
            if preprocessors is None else preprocessors
        
        postprocessors = _EsriNAGeocodeService.DEFAULT_POSTPROCESSORS \
            if postprocessors is None else postprocessors
        
        _EsriGeocodeService.__init__(self, preprocessors, postprocessors, settings)

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

        try:
            wkid = response_obj['spatialReference']['wkid']
        except KeyError:
            pass
        
        returned_candidates = [] # this will be the list returned
        try: 
            for rc in response_obj['candidates']:         
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
    
class EsriWGS(GeocodeService):
    """
    Class to geocode using the `ESRI World Geocoding service
    <http://geocode.arcgis.com/arcgis/geocoding.html>`_.

    This uses two endpoints -- one for single-line addresses,
    and one for multi-part addresses.
    """

    LOCATOR_MAP = {
        'PointAddress': 'rooftop',
        'StreetAddress': 'interpolation',
        'PostalExt': 'postal_specific', # accept ZIP+4
        'Postal': 'postal'
    }

    DEFAULT_PREPROCESSORS = [CancelIfPOBox()]

    DEFAULT_POSTPROCESSORS = [
        AttrFilter(['PointAddress',
                    'StreetAddress',
                    #'PostalExt',
                    #'Postal'
                   ],
                   'locator_type'),
        #AttrExclude(['USA_Postal'], 'locator'), #accept postal from everywhere but US (need PostalExt)
        AttrSorter(['PointAddress',
                    'StreetAddress',
                    #'PostalExt',
                    #'Postal'
                   ],
                   'locator_type'),
        AttrRename('locator', LOCATOR_MAP), # after filter to avoid searching things we toss out
        UseHighScoreIfAtLeast(99.8),
        ScoreSorter(),      
        GroupBy('match_addr'),
        GroupBy(('x', 'y')),
    ]

    _endpoint = 'http://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer'

    def _geocode(self, pq):
        """
        :arg PlaceQuery pq: PlaceQuery object to use for geocoding
        :returns: list of location Candidates
        """
        #: List of desired output fields
        #: See `ESRI docs <http://geocode.arcgis.com/arcgis/geocoding.html#output>_` for details
        outFields = ('Loc_name',
                     #'Shape',
                     'Score',
                     #'Match_Addr', #based on address standards for the country
                     #'Address', # returned by default
                     #'Country' # 3-digit ISO 3166-1 code for a country. Example: Canada = "CAN"
                     #'Admin',
                     #'DepAdmin',
                     #'SubAdmin',
                     #'Locality',
                     #'Postal',
                     #'PostalExt',
                     'Addr_Type',
                     #'Type',
                     #'Rank',
                     #'AddNum',
                     #'StPreDir',
                     #'StPreType',
                     #'StName',
                     #'StType',
                     #'StDir',
                     #'Side',
                     #'AddNumFrom',
                     #'AddNumTo',
                     #'AddBldg',
                     #'Ymax',
                     #'Ymin',
                     #'Xmin',
                     #'Xmax',
                     #'X',
                     #'Y',
                     'DisplayX',
                     'DisplayY',
                     #'LangCode',
                     #'Status',
                    )
        outFields = ','.join(outFields)
        query = dict(f='json', # default HTML. Other options are JSON and KMZ.
                     outFields=outFields,
                     #outSR=WKID, defaults to 4326
                     maxLocations=20, # default 1; max is 20
                     )

        # Postal-code only searches work in the single-line but not multipart geocoder
        # Remember that with the default postprocessors, postcode-level results will be eliminated
        if pq.query == pq.address == '' and pq.postal != '':
            pq.query = pq.postal

        if pq.query == '': # multipart
            method = 'findAddressCandidates'
            query = dict(query,
                         Address=pq.address, # commonly represents the house number and street name of a complete address
                         Admin1=pq.city,
                         Admin2=pq.state,
                         #Admin3=
                         #Admin4=
                         Postal=pq.postal,
                         #PostalExt=
                         CountryCode=pq.country, # full country name or ISO 3166-1 2- or 3-digit country code
                         )
            if pq.bounded and pq.viewbox is not None:
                query = dict(query, searchExtent=pq.viewbox.to_esri_wgs_json())            
        else: # single-line
            method = 'find'
            query = dict(query,
                         text=pq.query, # This can be a street address, place name, postal code, or POI.
                         sourceCountry=pq.country, # full country name or ISO 3166-1 2- or 3-digit country code
                         )
            if pq.bounded and pq.viewbox is not None:
                query = dict(query, bbox=pq.viewbox.to_esri_wgs_json())

        endpoint = self._endpoint + '/' + method
        response_obj = self._get_json_obj(endpoint, query)
        returned_candidates = [] # this will be the list returned
        try: 
            for location in response_obj['locations']:         
                c = Candidate()
                attributes = location['feature']['attributes']
                c.locator = attributes['Loc_name']
                c.locator_type = attributes['Addr_Type']
                c.score = attributes['Score']
                c.match_addr = location['name']
                #: "represents the actual location of the address. It differs from the X value"
                c.x = attributes['DisplayX'] 
                #: "represents the actual location of the address. It differs from the Y value"
                c.y = attributes['DisplayY']
                c.wkid = response_obj['spatialReference']['wkid']
                c.geoservice = self.__class__.__name__
                returned_candidates.append(c)
        except KeyError:
            pass
        return returned_candidates   

    def __init__(self, preprocessors=None, postprocessors=None, settings=None):
        preprocessors = EsriWGS.DEFAULT_PREPROCESSORS if preprocessors is None else preprocessors
        postprocessors = EsriWGS.DEFAULT_POSTPROCESSORS if postprocessors is None else postprocessors
        GeocodeService.__init__(self, preprocessors, postprocessors, settings)

class EsriWGSSSL(EsriWGS):
    """ 
    Class to geocode using the `ESRI World Geocoding service over SSL
    <https://geocode.arcgis.com/arcgis/geocoding.html>_`
    """
    _endpoint = 'https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer'

class MapQuest(GeocodeService):
    """
    Class to geocode using MapQuest licensed services.
    """
    _endpoint = 'http://www.mapquestapi.com/geocoding/v1/address'
    
    def _geocode(self, pq):
        def get_appended_location(location, **kwargs):
            """Add key/value pair to given dict only if value is not empty string."""
            for kw in kwargs:
                if kwargs[kw] != '':
                    location = dict(location, **{kw: kwargs[kw]})
            return location
        location = {}
        location = get_appended_location(location, street=pq.query)
        if location == {}:
            location = get_appended_location(location, street=pq.address)
        location = get_appended_location(location, city=pq.city, state=pq.state,
                                         postal=pq.postal, country=pq.country)
        json_ = dict(location=location)
        json_ = json.dumps(json_)
        logger.debug('MQ json: %s', json_)
        query = dict(key=unquote(self._settings['api_key']),
                     json=json_)
        if pq.viewbox is not None:
            query = dict(query, viewbox=pq.viewbox.to_mapquest_str())        
        response_obj = self._get_json_obj(self._endpoint, query)
        logger.debug('MQ RESPONSE: %s', response_obj)
        returned_candidates = [] # this will be the list returned
        for r in response_obj['results'][0]['locations']:
            c = Candidate()
            c.locator=r['geocodeQuality']
            c.confidence=r['geocodeQualityCode'] #http://www.mapquestapi.com/geocoding/geocodequality.html
            match_addr_elements = ['street', 'adminArea5', 'adminArea3',
                                   'adminArea2', 'postalCode'] # similar to ESRI
            c.match_addr = ', '.join([r[k] for k in match_addr_elements if k in r])
            c.x = r['latLng']['lng']
            c.y = r['latLng']['lat']
            c.wkid = 4326
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
    
class MapQuestSSL(MapQuest):
    _endpoint = 'https://www.mapquestapi.com/geocoding/v1/address'

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

    DEFAULT_PREPROCESSORS = [ReplaceRangeWithNumber()] # 766-68 Any St. -> 766 Any St. 
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
        query = {'q':pq.query,
                 'countrycodes':pq.country, # only takes ISO-2
                 'format':'json'}
        
        if pq.viewbox is not None:
            query = dict(query, **{'viewbox':pq.viewbox.to_mapquest_str(), 'bounded':pq.bounded})

        response_obj = self._get_json_obj(self._endpoint, query)
  
        returned_candidates = [] # this will be the list returned
        for r in response_obj:    
            c = Candidate()
            c.locator = 'parcel' # we don't have one but this is the closest match
            c.entity = '%s.%s' % (r['class'], r['type']) # ex.: "place.house"
            c.match_addr = r['display_name'] # ex. "Wolf Building, 340, N 12th St, Philadelphia, Philadelphia County, Pennsylvania, 19107, United States of America" #TODO: shorten w/ pieces
            c.x = float(r['lon']) # long, ex. -122.13 # cast to float in 1.3.4
            c.y = float(r['lat']) # lat, ex. 47.64 # cast to float in 1.3.4
            c.wkid = self._wkid
            c.geoservice = self.__class__.__name__
            returned_candidates.append(c)
        return returned_candidates
