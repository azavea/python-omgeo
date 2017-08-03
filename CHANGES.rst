Release Notes
+++++++++++++

v1.0, 2012-03-13
----------------
Initial Release

v1.1, 2012-03-22
----------------
Add ability to use ESRI premium tasks.

v1.2, 2012-04-04
----------------
Add Citizen Atlas (Washington DC) as a supported geocoder.

v1.3, 2012-04-20
----------------
Add ESRI SOAP locators as supported geocoders. Added suds
dependency. Remove default rejected entities from BING setting to a
postprocessor. Refactor constructors to fix bugs caused by mutable default
values.

v1.3.1, 2012-04-23
------------------
Refactor test runner. Support multiple fields in GroupBy
processor.

v1.3.2, 2012-04-25
------------------
Fix bug in ESRI geocoders in which defaults were appended
rather than overwritten.

v1.3.3, 2012-04-27
------------------
 * Add SnapPoints postprocessor.
 * Fix bug in tests (Bing was not being used even if the environment
   variable BING_MAPS_API_KEY was set.
 * Simplify ESRI ZIP processing
 * Improve logging

v1.3.4, 2012-05-11
------------------
 * Cast Nominatim coordinates returned in JSON from string to float.
   This was causing an error in the SnapPoints postprocessor added
   in v1.3.3, as the processor was attempting to evaluate mathematical
   equations using strings instead of numbers. A test was added to
   check that the types of the coordinates are successfully converted
   to floats.
 * Add test for SnapPoints postprocessor.
 * Change __unicode__() method for places.Candidate to display info
   indicating null or empty values, instead of just displaying "None".
   
v1.3.5, 2012-05-21
------------------
 * Geocoder().geocode() method can take one-line string OR PlaceQuery instance.
 * Improve speed by avoiding postprocessing of empty list
 * Add support for MapQuest licensed geocoding API using NAVTEQ data

v1.3.6, 2012-05-22
------------------
 * Add SSH support for MapQuest
 * Add CancelIfRegexInAttr preprocessor to avoid geocoding attempts if
   a PlaceQuery instance attribute matches the given regex (such as a 
   PO Box)
 * Add timeout option that can be included in the GeocodeService settings
   parameter. There is now a default timeout of 10 seconds.
 
v1.3.7, 2012-05-23
------------------
 * Add CancelIfPOBox preprocessor and tests
 * Add __unicode__() / __str__() method to PlaceQuery for string representation

v1.4.0, 2012-06-13
------------------
 * IMPORTANT: the Geocoder.geocode() method now returns a dictionary instead
   of a list of candidates. To just get a list of candidates, use
   Geocoder.get_candidates(). This functions the same the Geocoder.geocode()
   method in version 1.3.7.
 * New dictionary return type includes a list of candidates as well as a
   list of UpstreamResponseInfo objects, which include information about
   the upstream API call, including response time and errors.
 * Simplify error handling

v1.4.1, 2012-06-20
------------------
 * Wrap entire JSON result processing from geocoder in try/catch
 * Add separate logger for stats from geocoder

v1.4.3, 2012-08-09
------------------
 * Expand information in UpstreamResponseInfo object
 * Enhance logging

v1.4.4, 2012-08-13
------------------
 * Add original PlaceQuery to nested dict method response

v1.5.0, 2012-09-19
------------------
 * Add support for ESRI World Geocoder service
 * Add documentation built in Sphinx
   (available at python-omgeo.readthedocs.org)
 * Add shell script to rebuild, set API keys, and run tests
 * Move pre- and post-processor modules to package base
 * Add validation on Viewbox initialization
 * Add repr() methods for place objects, including graphical
   Viewbox representation
 * Modify ReplaceRangeWithNumber preprocessor to be friendly
   to ZIP+4 postal codes.

v1.5.1, 2012-09-20
------------------
 * Fix ordering of default postprocessors for EsriWGS geocoder
 * Improve handling of ZIP+4-only searching using EsriWGS
 * Add repr() method to UpstreamResponseInfo class
 * Minor documentation updates

v1.5.2, 2012-09-21
------------------
 * Fix bug in AttrMigrator.__repr__()

v1.5.3, 2012-09-25
------------------
 * Fix bug using wrong keys for ESRI
   findAddressCandidates endpoint in EsriWGS class

v1.5.4, 2012-10-09
------------------
 * Fix bug using wrong key for MapQuest postalCode

v1.5.5, 2013-01-18
------------------
 * Remove support for DC CitizenAtlas API
 * Add try...except to stats logging command in geocode method
 * Add option to raise exception on stats logging failure or add exception to general log.
 * Add more documentation for Geocoder methods

v1.5.6, 2013-01-18
------------------
 * Add test shell script template (test.dummy.sh) to source distribution.
 * Remove unneeded requirements.txt from source distribution.

v1.6.0, 2013-10-31
------------------
 * Add subregion and neighborhood parameters to queries
 * Allow HTTP request headers to be specified in geocoder settings
 * Documentation updates
 
v1.7.0, 2014-05-12
------------------
 * Add Census geocoder

v1.7.1, 2014-08-25
------------------
 * Return address components from US Census, EsriWGS geocoders.

v1.7.2, 2015-04-14
------------------
 * Support EsriWGS magicKey.

v1.8.0, 2016-01-22
------------------
 * Add support for Mapzen search.

v1.9.0, 2016-07-26
------------------
 * Add support for Google geocoder.

v1.9.2, 2017-03-06
------------------
 * Fix Google geocoder API key parameter.

v2.0.0, 2017-06-29
------------------
 * Remove usage of the ESRI WGS geocoder find endpoint.

v2.0.1, 2017-08-01
------------------
 * Change Census geocoder to use HTTPS

v3.0.0, 2017-08-03
------------------
 * Remove unsupported EsriNA and EsriEU services
 * Add authentication settings for the EsriWGS service
 * Add for_storage option for the EsriWGS service
