from base import GeocodeService
import logging
from omgeo.places import Candidate
from omgeo.preprocessors import CancelIfPOBox, CountryPreProcessor, ParseSingleLine
from omgeo.postprocessors import (AttrFilter, AttrRename, AttrSorter, UseHighScoreIfAtLeast,
                                  GroupBy, ScoreSorter)
from suds.client import Client

logger = logging.getLogger(__name__)


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
        'AN': 'AD',
        'AU': 'AT',
        'DA': 'DK',
        'GM': 'DE',
        'EI': 'IE',
        'LS': 'LI',
        'MN': 'MC',
        'PO': 'PT',
        'SP': 'ES',
        'SW': 'SE',
        'SZ': 'CH',
        'UK': 'GB',
        'VT': 'VC',
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
            'Address': location.address,
            'City': location.city,
            'Postcode': location.postal,
            'Country': location.country,
            'outfields': 'Loc_name',
            'f': 'json'
        }

        query = self.append_token_if_needed(query)

        response_obj = self._get_json_obj(self._endpoint, query)
        returned_candidates = []  # this will be the list returned
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
            logger.warning('Received unusual JSON result from geocode: %s, %s',
                           response_obj, ex)
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
            'SingleLine': location.query,
            'Address': location.address,
            'City': location.city,
            'State': location.state,
            'Zip': location.postal,
            'Country': location.country,
            'outfields': 'Loc_name,Addr_Type,Zip4_Type',
            'f': 'json'
        }

        query = self.append_token_if_needed(query)
        response_obj = self._get_json_obj(self._endpoint, query)

        try:
            wkid = response_obj['spatialReference']['wkid']
        except KeyError:
            pass

        returned_candidates = []  # this will be the list returned
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

    An optional (key) parameter can be passed to the PlaceQuery
    which will be passed as a magicKey to the find endpoint if
    using a single line address/text search. This allows omgeo
    to be used with the `Esri suggest endpoint
    <https://developers.arcgis.com/rest/geocode/api-reference/geocoding-suggest.htm>`_.

    Note: Based on tests using the magicKey parameter, it is
    recommended that a viewbox not be used with in conjuction
    with the magicKey. Additionally, address/search text passed
    via the query may be ignored when using a magicKey.
    """

    LOCATOR_MAP = {
        'PointAddress': 'rooftop',
        'StreetAddress': 'interpolation',
        'PostalExt': 'postal_specific',  # accept ZIP+4
        'Postal': 'postal'
    }

    DEFAULT_PREPROCESSORS = [CancelIfPOBox()]

    DEFAULT_POSTPROCESSORS = [
        AttrFilter(['PointAddress',
                    'StreetAddress',
                    # 'PostalExt',
                    # 'Postal'
                    ],
                   'locator_type'),
        # AttrExclude(['USA_Postal'], 'locator'), #accept postal from everywhere but US (need PostalExt)
        AttrSorter(['PointAddress',
                    'StreetAddress',
                    # 'PostalExt',
                    # 'Postal'
                    ],
                   'locator_type'),
        AttrRename('locator', LOCATOR_MAP),  # after filter to avoid searching things we toss out
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
                     # 'Shape',
                     'Score',
                     'Match_Addr',  # based on address standards for the country
                     # 'Address', # returned by default
                     # 'Country' # 3-digit ISO 3166-1 code for a country. Example: Canada = "CAN"
                     # 'Admin',
                     # 'DepAdmin',
                     # 'SubAdmin',
                     # 'Locality',
                     # 'Postal',
                     # 'PostalExt',
                     'Addr_Type',
                     # 'Type',
                     # 'Rank',
                     'AddNum',
                     'StPreDir',
                     'StPreType',
                     'StName',
                     'StType',
                     'StDir',
                     # 'Side',
                     # 'AddNumFrom',
                     # 'AddNumTo',
                     # 'AddBldg',
                     'City',
                     'Subregion',
                     'Region',
                     'Postal',
                     'Country',
                     # 'Ymax',
                     # 'Ymin',
                     # 'Xmin',
                     # 'Xmax',
                     # 'X',
                     # 'Y',
                     'DisplayX',
                     'DisplayY',
                     # 'LangCode',
                     # 'Status',
                     )
        outFields = ','.join(outFields)
        query = dict(f='json',  # default HTML. Other options are JSON and KMZ.
                     outFields=outFields,
                     # outSR=WKID, defaults to 4326
                     maxLocations=20,  # default 1; max is 20
                     )

        # Postal-code only searches work in the single-line but not multipart geocoder
        # Remember that with the default postprocessors, postcode-level results will be eliminated
        if pq.query == pq.address == '' and pq.postal != '':
            pq.query = pq.postal

        if pq.query == '':  # multipart
            method = 'findAddressCandidates'
            query = dict(query,
                         Address=pq.address,  # commonly represents the house number and street name of a complete address
                         Neighborhood=pq.neighborhood,
                         City=pq.city,
                         Subregion=pq.subregion,
                         Region=pq.state,
                         Postal=pq.postal,
                         # PostalExt=
                         CountryCode=pq.country,  # full country name or ISO 3166-1 2- or 3-digit country code
                         )
            if pq.bounded and pq.viewbox is not None:
                query = dict(query, searchExtent=pq.viewbox.to_esri_wgs_json())
        else:  # single-line
            method = 'find'
            magic_key = pq.key if hasattr(pq, 'key') else ''
            query = dict(query,
                         text=pq.query,  # This can be a street address, place name, postal code, or POI.
                         sourceCountry=pq.country,  # full country name or ISO 3166-1 2- or 3-digit country code
                         )
            if magic_key:
                query['magicKey'] = magic_key  # This is a lookup key returned from the suggest endpoint.
            if pq.bounded and pq.viewbox is not None:
                query = dict(query, bbox=pq.viewbox.to_esri_wgs_json())

        endpoint = self._endpoint + '/' + method
        response_obj = self._get_json_obj(endpoint, query)
        returned_candidates = []  # this will be the list returned
        try:
            if method == 'find':
                locations = response_obj['locations']
            else:
                locations = response_obj['candidates']

            for location in locations:
                c = Candidate()
                if method == 'find':  # singlepart
                    attributes = location['feature']['attributes']
                else:  # findAddressCandidates / multipart
                    attributes = location['attributes']
                c.match_addr = attributes['Match_Addr']
                c.locator = attributes['Loc_name']
                c.locator_type = attributes['Addr_Type']
                c.score = attributes['Score']
                c.x = attributes['DisplayX']  # represents the actual location of the address.
                c.y = attributes['DisplayY']
                c.wkid = response_obj['spatialReference']['wkid']
                c.geoservice = self.__class__.__name__

                # Optional address component fields.
                for in_key, out_key in [('City', 'match_city'), ('Subregion', 'match_subregion'),
                                        ('Region', 'match_region'), ('Postal', 'match_postal'),
                                        ('Country', 'match_country')]:
                    setattr(c, out_key, attributes.get(in_key, ''))
                setattr(c, 'match_streetaddr', self._street_addr_from_response(attributes))
                returned_candidates.append(c)
        except KeyError:
            pass
        return returned_candidates

    def _street_addr_from_response(self, attributes):
        """Construct a street address (no city, region, etc.) from a geocoder response.

        :param attributes: A dict of address attributes as returned by the Esri geocoder.
        """
        # The exact ordering of the address component fields that should be
        # used to reconstruct the full street address is not specified in the
        # Esri documentation, but the examples imply that it is this.
        ordered_fields = ['AddNum', 'StPreDir', 'StPreType', 'StName', 'StType', 'StDir']
        result = []
        for field in ordered_fields:
            result.append(attributes.get(field, ''))
        if any(result):
            return ' '.join([s for s in result if s])  # Filter out empty strings.
        else:
            return ''

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
