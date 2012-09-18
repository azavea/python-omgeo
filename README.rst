**The Oatmeal Geocoder - Python Edition**

``python-omgeo`` is a geocoding abstraction layer written in python.  Currently
supported geocoders:

* Bing
* Citizen Atlas (Washington DC)
* ESRI North American locator (REST & SOAP)
* ESRI European address locator (REST & SOAP)
* MapQuest Licensed Data API
* MapQuest-hosted Nominatim Open Data API

**Installation**::

    sudo pip install python-omgeo

**Documentation**

`Click here to view the documentation. <http://readthedocs.org/projects/python-omgeo/>`_

**Usage Example**

See the source for more info.  Here's a quick example.

>>> from omgeo import Geocoder 
>>> g = Geocoder() 
>>> result = g.geocode('340 12th St, Philadelphia PA')
>>> candidates = result['candidates']
>>> for c in candidates:
...   print c.x, c.y, c.match_addr
...
-75.15843 39.95872 340 N 12th St, Philadelphia, PA, 19107
-75.16136 39.94531 340 S 12th St, Philadelphia, PA, 19107

