**The Oatmeal Geocoder - Python Edition**

``python-omgeo`` is a geocoding abstraction layer written in python.  Currently
supported geocoders:

* Bing
* Citizen Atlas (Washington DC)
* ESRI European address locator (REST & SOAP)
* ESRI North American locator (REST & SOAP)
* ESRI `World Geocoding Service <http://geocode.arcgis.com/arcgis/geocoding.html>`_
* MapQuest Licensed Data API
* MapQuest-hosted Nominatim Open Data API

**Installation**::

    sudo pip install python-omgeo

**Documentation**

Docs are available in `HTML <http://python-omgeo.readthedocs.org/en/latest/>`_ 
or `PDF <http://media.readthedocs.org/pdf/python-omgeo/latest/python-omgeo.pdf>`_ format.

**Usage Example**

::

	>>> from omgeo import Geocoder 
	>>> g = Geocoder() 
	>>> g.geocode('340 12th St, Philadelphia PA')
	>>> candidates = result['candidates']
	{'candidates': [340 S 12th St, Philadelphia, PA, 19107 (-75.161461, 39.94532) via EsriWGS,
	  				340 N 12th St, Philadelphia, PA, 19107 (-75.158434, 39.958728) via EsriWGS],
	 'upstream_response_info': [EsriWGS 200 1047ms]}