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
	>>> result = g.geocode('340 12th St, Philadelphia PA')
	>>> candidates = result['candidates']
	>>> for c in candidates:
	...   print c.x, c.y, c.match_addr
	...
	-75.15843 39.95872 340 N 12th St, Philadelphia, PA, 19107
	-75.16136 39.94531 340 S 12th St, Philadelphia, PA, 19107
