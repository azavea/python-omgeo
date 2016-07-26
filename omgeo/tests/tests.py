#! /usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import sys
import unittest
from omgeo import Geocoder
from omgeo.places import Viewbox, PlaceQuery, Candidate
from omgeo.preprocessors import (CancelIfPOBox, CancelIfRegexInAttr, CountryPreProcessor,
                                 RequireCountry, ParseSingleLine, ReplaceRangeWithNumber)
from omgeo.postprocessors import (AttrFilter, AttrExclude, AttrRename,
                                  AttrSorter, AttrReverseSorter, UseHighScoreIfAtLeast,
                                  GroupBy, GroupByMultiple, ScoreSorter, SnapPoints)

BING_MAPS_API_KEY = os.getenv("BING_MAPS_API_KEY")
ESRI_MAPS_API_KEY = os.getenv("ESRI_MAPS_API_KEY")
MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
MAPZEN_API_KEY = os.getenv("MAPZEN_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logger = logging.getLogger(__name__)
logging.basicConfig(level='ERROR')


class OmgeoTestCase(unittest.TestCase):
    def assertEqual_(self, output, expected):
        """assertEqual with built-in error message"""
        self.assertEqual(output, expected, 'Expected "%s". Got "%s".' % (expected, output))

    def assertEqualCI_(self, output, expected, strip_commas=False):
        """Case-insensitive assertEqual with built-in error message"""
        self.assertEqual_(str(output).upper(), str(expected).upper())

    def assertOneCandidate(self, candidates):
        count = len(candidates)
        self.assertEqual(count > 0, True, 'No candidates returned.')
        self.assertEqual(count > 1, False, 'More than one candidate returned.')


class GeocoderTest(OmgeoTestCase):
    """Tests using various geocoding APIs. Requires internet connection."""
    g = None  # not set until set up
    BING_KEY_REQUIRED_MSG = 'Enter a Bing Maps API key to run the Bing tests.'
    MAPQUEST_KEY_REQUIRED_MSG = 'Enter a MapQuest API key to run the MapQuest tests. '\
                                'Keys can be obtained at http://developer.mapquest.com/.'
    MAPZEN_KEY_REQUIRED_MSG = 'Enter a Mapzen Search API key to run Mapzen ' \
                              'tests. Keys can be obtained at ' \
                              'https://mapzen.com/developers/sign_in.'
    ESRI_KEY_REQUIRED_MSG = 'Enter an ESRI API key to run ESRI SOAP tests.'
    GOOGLE_KEY_REQUIRED_MSG = 'Enter a Google API key to run Google tests.'

    def setUp(self):
        # Viewbox objects - callowhill is from BSS Spring Garden station to Wash. Sq.
        vb = {'callowhill': Viewbox(-75.162628, 39.962769, -75.150963, 39.956322)}
        # PlaceQuery objects
        self.pq = {  # North American Addresses:
            'azavea': PlaceQuery('340 N 12th St Ste 402 Philadelphia PA'),
            'ambiguous_azavea': PlaceQuery('340 12th St Ste 402 Philadelphia PA'),
            'zip_plus_4_in_postal_plus_country': PlaceQuery(postal='19127-1115', country='US'),
            'wolf': PlaceQuery('Wolf Building'),
            'wolf_philly': PlaceQuery('Wolf Building, Philadelphia PA'),
            'wolf_bounded': PlaceQuery('Wolf Building', bounded=True, viewbox=vb['callowhill']),
            'bounded_340_12th': PlaceQuery('340 12th St, Philadelphia PA',
                                           bounded=True, viewbox=vb['callowhill']),
            'alpha_774R_W_Central_Ave': PlaceQuery('774R W Central Ave Alpha NJ'),
            'alpha_774_W_Central_Ave_Rear': PlaceQuery('774 W Central Ave Rear, Alpha NJ'),
            '8_kirkbride': PlaceQuery('8 Kirkbride Rd 08822'),
            'george_washington': PlaceQuery('201 W Montmorency Blvd, George, Washington'),
            'pine_needles_dr': PlaceQuery('11761 pine needles providence forge'),
            'pine_needles_ct': PlaceQuery('5328 pine needles providence forge'),
            'pine_needles_terr': PlaceQuery('5359 pine needles providence forge'),
            'moorestown_hyphenated': PlaceQuery('111-113 W Main St Moorestown NJ'),
            'willow_street': PlaceQuery('2819F Willow Street Pike Willow Street PA'),
            'willow_street_parts': PlaceQuery(address='2819F Willow Street Pike',
                                              city='Willow Street', state='PA', country='US'),
            'quebec': PlaceQuery('756 Rue Berri Montreal QC', country='CA'),
            'quebec_accent': PlaceQuery('527 Ch. Beauséjour, Saint-Elzéar-de-Témiscouata QC'),
            'quebec_hyphenated': PlaceQuery('227-227A Rue Commerciale, Saint-Louis-du-Ha! Ha! QC'),
            'senado_mx': PlaceQuery('Paseo de la Reforma 135, Tabacalera, Cuauhtémoc, Distrito Federal, 06030'),
            'senado_mx_struct': PlaceQuery(address='Paseo de la Reforma 135', neighborhood='Tabacalera, Cuauhtémoc', subregion='', state='Distrito Federal', postal='06030', country='MX'),
            # European Addresses:
            'london_pieces': PlaceQuery(address='31 Maiden Lane', city='London', country='UK'),
            'london_one_line': PlaceQuery('31 Maiden Lane, London WC2E', country='UK'),
            'london_pieces_hyphenated': PlaceQuery(address='31-32 Maiden Lane', city='London',
                                                   country='UK'),
            'london_one_line_hyphenated': PlaceQuery('31-32 Maiden Lane London WC2E', country='UK'),
            # Oceanian Addresses:
            'karori': PlaceQuery('102 Karori Road Karori Wellington', country='NZ'),
        }

        if BING_MAPS_API_KEY is not None:
            bing_settings = dict(api_key=BING_MAPS_API_KEY)
            self.g_bing = Geocoder([['omgeo.services.Bing', {'settings': bing_settings}]])

        if MAPQUEST_API_KEY is not None:
            mapquest_settings = dict(api_key=MAPQUEST_API_KEY)
            self.g_mapquest = Geocoder([['omgeo.services.MapQuest',
                                       {'settings': mapquest_settings}]])
            self.g_mapquest_ssl = Geocoder([['omgeo.services.MapQuestSSL',
                                           {'settings': mapquest_settings}]])

        if MAPZEN_API_KEY is not None:
            mapzen_settings = dict(api_key=MAPZEN_API_KEY)
            self.g_mapzen = Geocoder([['omgeo.services.Mapzen', {'settings': mapzen_settings}]])

        if GOOGLE_API_KEY is not None:
            self.g_google = Geocoder([['omgeo.services.Google',
                                     {'settings': {'api_key': GOOGLE_API_KEY}}]])

        #: main geocoder used for tests, using default APIs
        self.g = Geocoder()

        # Set up params for old ESRI rest services:
        esri_settings = {} if ESRI_MAPS_API_KEY is None else {'api_key': ESRI_MAPS_API_KEY}
        old_esri_params = {'settings': esri_settings}

        # geocoders using individual services
        # self.g_dc = Geocoder([['omgeo.services.CitizenAtlas', {}]])
        self.g_esri_na = Geocoder([['omgeo.services.EsriNA', old_esri_params]])
        self.g_esri_eu = Geocoder([['omgeo.services.EsriEU', old_esri_params]])
        self.g_esri_wgs = Geocoder([['omgeo.services.EsriWGS', {}]])
        if ESRI_MAPS_API_KEY is not None:  # SOAP services are subscriber-only now
            self.g_esri_na_soap = Geocoder([['omgeo.services.EsriNASoap', {}]])
            self.g_esri_eu_soap = Geocoder([['omgeo.services.EsriEUSoap', {}]])

        if MAPQUEST_API_KEY is not None:  # MapQuest's open Nominatime API now also requires a key
            self.g_nom = Geocoder([['omgeo.services.Nominatim', {}]])

        self.g_census = Geocoder([['omgeo.services.USCensus', {}]])

        ESRI_WGS_LOCATOR_MAP = {'PointAddress': 'rooftop',
                                'StreetAddress': 'interpolation',
                                'PostalExt': 'postal_specific',  # accept ZIP+4
                                'Postal': 'postal'}
        ESRI_WGS_POSTPROCESSORS_POSTAL_OK = [
            AttrExclude(['USA.Postal'], 'locator'),  # accept postal from everywhere but US (need PostalExt)
            AttrFilter(['PointAddress', 'StreetAddress', 'PostalExt', 'Postal'], 'locator_type'),
            AttrSorter(['PointAddress', 'StreetAddress', 'PostalExt', 'Postal'], 'locator_type'),
            AttrRename('locator', ESRI_WGS_LOCATOR_MAP),  # after filter to avoid searching things we toss out
            UseHighScoreIfAtLeast(99.8),
            ScoreSorter(),
            GroupBy('match_addr'),
            GroupBy(('x', 'y')),
        ]
        GEOCODERS_POSTAL_OK = [['omgeo.services.EsriWGS', {'postprocessors': ESRI_WGS_POSTPROCESSORS_POSTAL_OK}]]
        self.g_esri_wgs_postal_ok = Geocoder(GEOCODERS_POSTAL_OK)

        #: geocoder with fast timeout
        self.impatient_geocoder = Geocoder([['omgeo.services.EsriWGS', {'settings': {'timeout': 0.01}}]])

    def tearDown(self):
        pass

    def test_geocode_azavea(self):
        candidates = self.g.get_candidates(self.pq['azavea'])
        self.assertOneCandidate(candidates)

    def test_impatiently_geocode_azavea(self):
        candidates = self.impatient_geocoder.get_candidates(self.pq['azavea'])
        self.assertEqual(len(candidates) == 0, True,
                         'Candidates were unexpectedly returned in under 10ms.')

    @unittest.skipIf(ESRI_MAPS_API_KEY is None, ESRI_KEY_REQUIRED_MSG)
    def test_geocode_snap_points_1(self):
        """
        Geocoder expected to return the same place twice -- one with city as Flemington,
        and one with city as Readington Twp. This test checks that only one is picked.
        """
        candidates = self.g_esri_na.get_candidates(self.pq['8_kirkbride'])
        self.assertOneCandidate(candidates)

    @unittest.skipIf(BING_MAPS_API_KEY is None, BING_KEY_REQUIRED_MSG)
    def test_geocode_snap_points_2(self):
        """
        Bing geocoder expected to return the same place twice -- one with city as Alpha,
        and one with city as Phillipsburg. This test checks that only one is picked.
        """
        candidates = self.g_bing.get_candidates(self.pq['alpha_774_W_Central_Ave_Rear'])
        self.assertOneCandidate(candidates)

    def test_geocode_esri_wgs_senado_mx(self):
        """
        Attempt to geocode ``Paseo de la Reforma 135, Tabacalera,
        Cuauhtémoc, Distrito Federal, 06030``.
        """
        candidates = self.g_esri_wgs.get_candidates(self.pq['senado_mx'])
        self.assertOneCandidate(candidates)
        search_text = 'Paseo de la Reforma 135'
        self.assertEqual(search_text in candidates[0].match_addr, True,
                         '"%s" not found in match_addr. Got "%s".'
                         % (search_text, candidates[0].match_addr))

    def test_geocode_structured_esri_wgs_senado_mx(self):
        """
        Attempt to geocode ``Paseo de la Reforma 135, Tabacalera,
        Cuauhtémoc, Distrito Federal, 06030`` using a structured query to
        EsriWGS.
        """
        candidates = self.g_esri_wgs.get_candidates(self.pq['senado_mx_struct'])
        self.assertOneCandidate(candidates)
        search_text = 'Paseo de la Reforma 135'
        self.assertEqual(search_text in candidates[0].match_addr, True,
                         '"%s" not found in match_addr. Got "%s".'
                         % (search_text, candidates[0].match_addr))

    def test_geocode_esri_wgs_340_12th_bounded(self):
        """
        Trying to geocode ``340 12th St, Philadelphia PA`` would normally return results
        for both ``340 N 12th St`` and ``340 S 12th St``. Using a bounding box around Callowhill,
        we should only get the former.
        """
        candidates = self.g_esri_wgs.get_candidates(self.pq['bounded_340_12th'])
        self.assertOneCandidate(candidates)
        self.assertEqual('340 N 12th' in candidates[0].match_addr, True,
                         '"340 N 12th" not found in match_addr. Got "%s"' % candidates[0].match_addr)

    def test_geocode_esri_wgs_zip_plus_4(self):
        """Check that geocoding 19127-1112 returns one result."""
        candidates = self.g_esri_wgs_postal_ok.get_candidates(self.pq['zip_plus_4_in_postal_plus_country'])
        self.assertOneCandidate(candidates)

    def test_geocode_esri_wgs_multipart(self):
        """Check that geocoding multipart address returns one result."""
        candidates = self.g_esri_wgs.get_candidates(self.pq['willow_street_parts'])
        self.assertOneCandidate(candidates)

    def test_bounded_no_viewbox(self):
        """
        Should return a nice error saying that PlaceQuery can't be bounded without Viewbox.
        """
        pass

    @unittest.skipIf(ESRI_MAPS_API_KEY is None, ESRI_KEY_REQUIRED_MSG)
    def test_geocode_esri_na_us_soap(self):
        """Test ESRI North America SOAP geocoder"""
        location = '340 N 12th St., Philadelphia, PA, US'
        candidates = self.g_esri_na_soap.get_candidates(location)
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned for %s.' % location)

    @unittest.skipIf(ESRI_MAPS_API_KEY is None, ESRI_KEY_REQUIRED_MSG)
    def test_geocode_esri_na_us(self):
        """Test ESRI North America REST geocoder"""
        location = '340 N 12th St., Philadelphia, PA, US'
        candidates = self.g_esri_na.get_candidates(location)
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned for %s.' % location)

    @unittest.skipIf(ESRI_MAPS_API_KEY is None, ESRI_KEY_REQUIRED_MSG)
    def test_geocode_esri_eu_soap(self):
        """Test ESRI Europe SOAP geocoder"""
        candidates = self.g_esri_eu_soap.get_candidates(PlaceQuery(
            address='31 Maiden Lane', city='London', country='UK'))
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(ESRI_MAPS_API_KEY is None, ESRI_KEY_REQUIRED_MSG)
    def test_geocode_esri_na_nz(self):
        """
        Test ESRI North America REST geocoder using a city in New Zealand.
        """
        candidates = self.g_esri_na.get_candidates(self.pq['karori'])
        self.assertEqual(len(candidates) > 0, False,
                         'Found New Zealand address when this should only'
                         'be using the North American ESRI geocoder. '
                         'Candidates are %s.' % candidates)

    @unittest.skipIf(BING_MAPS_API_KEY is None, BING_KEY_REQUIRED_MSG)
    def test_geocode_bing(self):
        """Test Azavea's address using Bing geocoder"""
        candidates = self.g_bing.get_candidates(self.pq['azavea'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(MAPQUEST_API_KEY is None, MAPQUEST_KEY_REQUIRED_MSG)
    def test_geocode_mapquest(self):
        """Test Azavea's address using MapQuest geocoder."""
        candidates = self.g_mapquest.get_candidates(self.pq['azavea'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(MAPQUEST_API_KEY is None, MAPQUEST_KEY_REQUIRED_MSG)
    def test_geocode_mapquest_ssl(self):
        """Test Azavea's address using secure MapQuest geocoder."""
        candidates = self.g_mapquest_ssl.get_candidates(self.pq['azavea'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(MAPZEN_API_KEY is None, MAPZEN_KEY_REQUIRED_MSG)
    def test_geocode_mapzen(self):
        """Test Azavea's address using Mapzen geocoder"""
        candidates = self.g_mapzen.get_candidates(self.pq['azavea'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(MAPQUEST_API_KEY is None, MAPQUEST_KEY_REQUIRED_MSG)
    def test_geocode_nom(self):
        """
        Test 1200 Callowhill Street using Nominatim geocoder.
        Also check to make sure coordinate values are floats and not some other data type.
        """
        candidates = self.g_nom.get_candidates(PlaceQuery('1200 Callowhill St, Philadelphia, PA'))
        x_type = type(candidates[0].x)
        y_type = type(candidates[0].y)
        self.assertEqual(x_type == float, True, 'x coord is of type %s instead of float' % x_type)
        self.assertEqual(y_type == float, True, 'y coord is of type %s instead of float' % y_type)
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    def test_geocode_census(self):
        """Test Azavea's address using US Census geocoder."""
        candidates = self.g_census.get_candidates(PlaceQuery('1200 Callowhill St, Philadelphia, PA'))
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    def test_EsriWGS_address_components(self):
        """Make sure EsriWGS returns address components"""
        candidate = self.g_esri_wgs.get_candidates(self.pq['azavea'])[0]
        self._test_address_components(candidate)

    def test_census_address_components(self):
        """Make sure census geocoder returns address components"""
        candidate = self.g_census.get_candidates(self.pq['azavea'])[0]
        self._test_address_components(candidate)

    def test_geocode_dupepicker(self):
        """
        Check that '340 12th St returns results'
        """
        candidates = self.g.get_candidates(self.pq['ambiguous_azavea'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')

    @unittest.skipIf(BING_MAPS_API_KEY is None, BING_KEY_REQUIRED_MSG)
    def test_geocode_karori(self):
        """
        Check that '102 Karori Road Karori Wellington' returns an address
        with the correct house number and postcode.
        """
        candidates = self.g_bing.get_candidates(self.pq['karori'])
        self.assertEqual(len(candidates) > 0, True, 'No candidates returned.')
        self.assertEqual(any([('102' in c.match_addr and '6012' in c.match_addr) for c in candidates]),
            True, 'Could not find bldg. no. "102" and postcode "6012" in any address.')

    def _test_address_components(self, candidate):
            for field in ['match_streetaddr', 'match_city', 'match_subregion', 'match_region',
                          'match_postal', 'match_country']:
                self.assertIsNotNone(getattr(candidate, field, None),
                                     msg='Missing address component %s' % field)

    def _test_geocode_results_all_(self, verbosity=0, geocoder=Geocoder(),
                                   expected_results=16):
        """
        Geocode a list of addresses. Some of these only work with Bing so
        fewer results are expected when Bing is not used as a geocoder.
        """
        if verbosity > 1:
            logger.setLevel(logging.INFO)

        queries_with_results = 0
        for place in self.pq:
            logger.info(place)
            logger.info(len(place) * '-')
            candidates = geocoder.get_candidates(self.pq[place])
            if len(candidates) == 0:
                logger.info('Input: %s\n(no results)' % self.pq[place].query)
            else:
                queries_with_results += 1
                logger.info('Input:  %s' % self.pq[place].query)
                logger.info(map(lambda c: 'Output: %r (%s %s)\n' %
                                (c.match_addr,
                                 c.geoservice,
                                 [c.locator, c.score, c.confidence, c.entity]),
                                candidates))
        self.assertEqual(expected_results, queries_with_results,
                         'Got results for %d of %d queries.' % (queries_with_results, len(self.pq)))

    def _test_geocode_results_all(self):
        if BING_MAPS_API_KEY is None:
            expected_results = 16
        else:
            self.g.add_source(['omgeo.services.Bing', {'settings': {'api_key': BING_MAPS_API_KEY}}])
            expected_results = len(self.pq)
        self._test_geocode_results_all_(geocoder=self.g, expected_results=expected_results)

    def test_esri_geocoder_na_default_override(self):
        """
        Test for default argument bug in 3.1 --
        EsriNA and EsriEU append processors rather than replace them
        """
        geocoder = Geocoder([['omgeo.services.EsriNA',
                            {'postprocessors': [AttrFilter([
                                'rooftop',
                                'interpolation',
                                'postal_specific'],
                                'locator')]}]])

        self.assertEqual(1, len(geocoder._sources[0]._postprocessors),
                         'EsriNA geocoder incorrectly processed defaults')
        self.assertEqual('AttrFilter', geocoder._sources[0]._postprocessors[0].__class__.__name__,
                         'EsriNA geocoder incorrectly processed defaults')

    def test_esri_geocoder_eu_default_override(self):
        """
        Test for default argument bug in 3.1 --
        EsriNA and EsriEU append processors rather than replace them
        """
        geocoder = Geocoder([['omgeo.services.EsriEU',
                            {'postprocessors': [AttrFilter([
                                'rooftop',
                                'interpolation',
                                'postal_specific'],
                                'locator')]}]])

        self.assertEqual(1, len(geocoder._sources[0]._postprocessors),
                         'EsriEU geocoder incorrectly processed defaults')
        self.assertEqual('AttrFilter',
                         geocoder._sources[0]._postprocessors[0].__class__.__name__,
                         'EsriEU geocoder incorrectly processed defaults')

    @unittest.skipIf(GOOGLE_API_KEY is None, GOOGLE_KEY_REQUIRED_MSG)
    def test_google_geocode_azavea(self):
        candidates = self.g_google.get_candidates(self.pq['azavea'])
        self.assertOneCandidate(candidates)

    @unittest.skipIf(GOOGLE_API_KEY is None, GOOGLE_KEY_REQUIRED_MSG)
    def test_google_geocode_multipart(self):
        """Check that geocoding multipart address returns one result."""
        candidates = self.g_google.get_candidates(self.pq['willow_street_parts'])
        self.assertOneCandidate(candidates)

    @unittest.skipIf(GOOGLE_API_KEY is None, GOOGLE_KEY_REQUIRED_MSG)
    def test_google_country_filter(self):
        candidates = self.g_google.get_candidates('York')
        self.assertOneCandidate(candidates)
        self.assertEqual(candidates[0].match_region, 'PA')
        candidates = self.g_google.get_candidates(PlaceQuery('York', country='UK'))
        self.assertOneCandidate(candidates)
        self.assertEqual(candidates[0].match_country, 'GB')


class GeocoderProcessorTest(OmgeoTestCase):
    """Tests using various pre- and post-processors."""
    def setUp(self):
        # places
        self.pq_us = PlaceQuery('1200 Callowhill St, Philadelphia, PA 19107')
        self.pq_uk = PlaceQuery('32 Bond Road, Ste A, Surbiton, Surrey KT6')
        self.pq_uk_with_country_UK = PlaceQuery('32 Bond Road, Ste A, Surbiton, Surrey KT6', country='UK')
        self.pq_uk_with_country_GB = PlaceQuery('32 Bond Road, Ste A, Surbiton, Surrey KT6', country='GB')

        # candidates
        self.good = Candidate(match_addr='123 Any St', locator='address', score=85.3)
        self.better = Candidate(match_addr='123 Any St', locator='parcel', score=92)
        self.best = Candidate(match_addr='123 Any St', locator='rooftop', score=100)
        self.wolf_good = Candidate(match_addr='1200 Callowhill St', locator='address', score=76)
        self.wolf_better = Candidate(match_addr='1200 Callowhill St', locator='parcel', score=90)
        self.wolf_best = Candidate(match_addr='1200 Callowhill St', locator='rooftop',
                                   score=99.9, x=-75.158, y=39.959)
        self.wolf_340 = Candidate(match_addr='340 N 12th St', locator='rooftop',
                                  score=99.5, x=-75.158, y=39.959)  # same coords
        self.inky = Candidate(match_addr='324 N Broad St', locator='rooftop',
                              score=99.9, x=-75.163, y=39.959)  # same y
        self.capt_thomas = Candidate(match_addr='843 Callowhill St', locator='rooftop',
                                     score=99.9, x=-75.163, y=39.959)  # same y
        self.reading_term = Candidate(match_addr='1200 Arch St', locator='rooftop',
                                      score=99.9, x=-75.163, y=39.953)  # same x

        self.locators_worse_to_better = ['address', 'parcel', 'rooftop']

    def tearDown(self):
        pass

    def test_pro_country_CountryPreProcessor(self):
        """Test CountryPreProcessor"""
        acceptable_countries = ['US', 'UK']
        country_map = {'GB': 'UK'}  # 'from': 'to'
        place_in = self.pq_uk_with_country_GB
        place_out = CountryPreProcessor(acceptable_countries, country_map).process(place_in)
        country_exp = 'UK'
        self.assertEqual_(place_out.country, country_exp)

    def test_pro_country_RequireCountry(self):
        """Test RequireCountry preprocessor."""
        place_in = self.pq_us
        place_out = RequireCountry().process(place_in)
        place_exp = False
        self.assertEqual_(place_out, place_exp)

    def test_pro_CancelIfRegexInAttr(self):
        """Test CancelIfRegexInAttr preprocessor."""
        place_in = PlaceQuery('PO Box 123, Philadelphia, PA')
        place_out = CancelIfRegexInAttr(regex="po box", attrs=('query',)).process(place_in)
        place_exp = False
        self.assertEqual_(place_out, place_exp)

    def test_pro_CancelIfRegexInAttr_case_sensitive(self):
        """Test CancelIfRegexInAttr preprocessor using case-sensitive option."""
        place_in = PlaceQuery('PO Box 123, Philadelphia, PA')
        place_out = CancelIfRegexInAttr(regex="PO BOX", attrs=('query',),
                                        ignorecase=False).process(place_in)
        place_exp = place_in  # we should still have it because PO BOX does not match exactly
        self.assertEqual_(place_out, place_exp)

    def test_pro_CancelIfPOBox(self):
        """Test CancelIfPOBox preprocessor."""
        place_in = PlaceQuery('PO Box 123, Philadelphia, PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='PO Box 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P.O Box 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P  O  box 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P.O. Box 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P.O. Box K', city='New Stanton', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='PO. Box K', city='New Stanton', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P.O.B. 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='P.O. BX123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery(address='POB 123', city='Philadelphia', state='PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery('POBOX 123, Philadelphia, PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, False)

        place_in = PlaceQuery('1200 Callowhill St, PO Box 466, Philadelphia, PA')
        place_out = CancelIfPOBox().process(place_in)
        self.assertEqual_(place_out, place_in)  # should still geocode because we a physical address

    def test_pro_filter_AttrFilter_exact(self):
        """Test AttrFilter postprocessor."""
        good_values = ['roof', 'parcel']
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.better]  # just the one with the parcel locator
        candidates_out = AttrFilter(good_values, 'locator', exact_match=True).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_filter_AttrFilter_inexact(self):
        """Test AttrFilter postprocessor with ``exact_match=False``."""
        good_values = ['roof', 'parcel']
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.best, self.better]  # roof is a substr of rooftop
        candidates_out = AttrFilter(good_values, 'locator', exact_match=False).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_filter_AttrExclude_exact(self):
        """Test AttrExclude with ``exact_match=True``."""
        bad_values = ['address', 'parc']
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.best, self.better]
        # The candidate with the 'parcel' locator stays because 'parcel' is not in bad values
        # and the processor by default only looks for exact matches against bad_values.
        candidates_out = AttrExclude(bad_values, 'locator', exact_match=True).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_filter_AttrExclude_inexact(self):
        """Test AttrExclude with ``exact_match=False``."""
        bad_values = ['address', 'parc']
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.best]
        # This can be confusing. There is only one because the match does NOT have to be exact, but
        # we are using this processor to EXCLUDE values, so an inexact match will result in fewer candidates
        candidates_out = AttrExclude(bad_values, 'locator', exact_match=False).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_postpro_GroupBy(self):
        """Test GroupBy postprocessor."""
        candidates_in = [self.best, self.good, self.better, self.wolf_best, self.wolf_good]
        candidates_exp = [self.best, self.wolf_best]
        candidates_out = GroupBy('match_addr').process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_postpro_GroupByMultiple(self):
        candidates_in = [self.wolf_best, self.wolf_340]
        candidates_exp = [self.wolf_best]
        candidates_out = GroupBy(('x', 'y')).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_parsing_ParseSingleLine(self):
        """Test ParseSingleLine preprocessor using single-line UK address."""
        place_in = PlaceQuery('32 Bond Road, Surbiton, Surrey KT6 7SH')
        place_out = ParseSingleLine().process(place_in)
        self.assertEqual_(place_out.address, '32 Bond Road')
        self.assertEqual_(place_out.city, 'Surbiton, Surrey')
        self.assertEqual_(place_out.postal, 'KT6 7SH')

    def test_pro_rename_AttrRename_inexact(self):
        """Test AttrRename postprocessor using partial search string."""
        candidates_in = [self.best]
        locator_exp = 'el_techo'
        candidates_out = AttrRename('locator', {'oofto': 'el_techo'}).process(candidates_in)
        self.assertEqual_(candidates_out[0].locator, locator_exp)

    def test_pro_rename_AttrRename_exact(self):
        """Test AttrRename postprocessor using exact search string."""
        candidates_in = [self.best]
        locator_exp = 'el_techo'
        candidates_out = AttrRename('locator', {'rooftop': 'el_techo'}).process(candidates_in)
        self.assertEqual_(candidates_out[0].locator, locator_exp)

    def test_pro_scoring_UseHighScoreIfAtLeast(self):
        """Test UseHighScoreIfAtLeast postprocessor."""
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.best, self.better]
        candidates_out = UseHighScoreIfAtLeast(90).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_scoring_ScoreSorter(self):
        """Test ScoreSorter postprocessor."""
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.best, self.better, self.good]
        candidates_out = ScoreSorter().process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_scoring_ScoreSorter_asc(self):
        """Test ScoreSorter postprocessor with ``reverse=False``."""
        candidates_in = [self.best, self.good, self.better]
        candidates_exp = [self.good, self.better, self.best]
        candidates_out = ScoreSorter(reverse=False).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_sort_AttrSorter(self):
        """Test AttrSorter postprocessor."""
        candidates_in = [self.better, self.best, self.good]
        candidates_exp = [self.good, self.better, self.best]
        candidates_out = AttrSorter(self.locators_worse_to_better).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_sort_AttrReverseSorter(self):
        """Test AttrReverseSorter postprocessor."""
        candidates_in = [self.better, self.best, self.good]
        candidates_exp = [self.best, self.better, self.good]  # reverse order of self.locators_worse_to_better
        candidates_out = AttrReverseSorter(self.locators_worse_to_better).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)

    def test_pro_streetnumber_ReplaceRangeWithNumber(self):
        """Test ReplaceRangeWithNumber preprocessor."""
        place_in = PlaceQuery('4452-54 Main Street, Philadelphia')  # Mom's Pizza in Manayunk
        place_out = ReplaceRangeWithNumber().process(place_in)
        query_exp = '4452 Main Street, Philadelphia'
        self.assertEqual_(place_out.query, query_exp)

        zip_plus_4 = '19127-1112'
        place_in = PlaceQuery(zip_plus_4)  # sets PlaceQuery.query to zip_plus_4 on init
        place_out = ReplaceRangeWithNumber().process(place_in)
        self.assertEqual_(place_out.query, zip_plus_4)

    def test_pro_SnapPoints(self):
        """Take two candidates within 50 metres and eliminate one."""
        candidates_in = [Candidate(match_addr='340 N 12th St, Philadelphia, PA, 19107',
                                   x=-75.158433167, y=39.958727992),
                         Candidate(match_addr='1200 Callowhill St, Philadelphia, PA, 19123',
                                   x=-75.158303781, y=39.959040684)]  # about 40m away
        candidates_exp = [candidates_in[0]]  # should just keep the first one.
        candidates_out = SnapPoints(distance=50).process(candidates_in)
        self.assertEqual_(candidates_out, candidates_exp)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    unittest.main()
