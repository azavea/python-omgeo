**OMGeo - Python Edition**

``python-omgeo`` is a geocoding abstraction layer written in python.  Currently
supported geocoders:

* `US Census Geocoder <https://www.census.gov/geo/maps-data/data/geocoder.html>`_
* `Bing Maps REST Locations API <http://msdn.microsoft.com/en-us/library/ff701715.aspx>`_
* `ESRI World Geocoding Service <http://resources.arcgis.com/en/help/arcgis-online-geocoding-rest-api/>`_
* `MapQuest Licensed Data API <http://developer.mapquest.com/web/products/dev-services/geocoding-ws>`_
* `MapQuest-hosted Nominatim Open Data API <http://developer.mapquest.com/web/products/open/geocoding-service>`_
* `Mapzen Search API <https://mapzen.com/projects/search/>`_
* `Google geocoder <https://developers.google.com/maps/documentation/geocoding/intro>`_

.. NOTE::
   Check out `this project's page on GitHub <https://github.com/azavea/python-omgeo/>`_.

**Installation**::

    sudo pip install python-omgeo

**Documentation**

Docs are available in `HTML <http://python-omgeo.readthedocs.org/en/latest/>`_ 
or `PDF <http://media.readthedocs.org/pdf/python-omgeo/latest/python-omgeo.pdf>`_ format.

**Usage Example**

Make a new geocoder and geocode and address::

    >>> from omgeo import Geocoder 
    >>> g = Geocoder() 
    >>> result = g.geocode('340 12th St, Philadelphia PA')

Take a look at the result::

    >>> result
    {'candidates': [
      <340 S 12th St, Philadelphia, PA, 19107 (-75.161461, 39.94532) EsriWGS>,
      <340 N 12th St, Philadelphia, PA, 19107 (-75.158434, 39.958728) EsriWGS>
     ],
     'upstream_response_info': [<EsriWGS 1054ms>]}

Take a closer look at the information in our address Candidate objects::

    >>> [c.__dict__ for c in result["candidates"]]
	[{'geoservice': 'EsriWGS',
	  'locator': u'USA.AddressPoint',
	  'locator_type': u'PointAddress',
	  'match_addr': u'340 S 12th St, Philadelphia, PA, 19107',
	  'score': 90.87,
	  'wkid': 4326,
	  'x': -75.161461,
	  'y': 39.94532},
	 {'geoservice': 'EsriWGS',
	  'locator': 'interpolation',
	  'locator_type': u'StreetAddress',
	  'match_addr': u'340 N 12th St, Philadelphia, PA, 19107',
	  'score': 90.87,
	  'wkid': 4326,
	  'x': -75.158434,
	  'y': 39.958728}]

Some geocoders (EsriWGS and US Census) can return address components in addition to the
full address::

    >>> [{'geoservice': 'EsriWGS',
        'locator': 'interpolation',
        'locator_type': u'StreetAddress',
        'match_addr': u'340 N 12th St, Phila, Pennsylvania, 19107',
        'match_city': u'Phila',
        'match_country': u'USA',
        'match_postal': u'19107',
        'match_region': u'Pennsylvania',
        'match_streetaddr': u'340 N 12th St',
        'match_subregion': u'',
        'score': 90.1,
        'wkid': 4326,
        'x': -75.158384,
        'y': 39.958774}]

These are optional; their existence may change depending on the response from the geocoder.

**Testing**

There is a shell script in the root of the repository called *test.dummy.sh*.
Copy it using ``cp test.dummy.sh test.sh``. Edit *test.sh* to include the
API keys that you obtained from the given geocoding service providers. Then, run
the tests using ``./test.sh``.
