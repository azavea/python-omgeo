**The Oatmeal Geocoder - Python Edition**

``python-omgeo`` is a geocoding abstraction layer written in python.  Currently
supported geocoders:

* Bing
* Citizen Atlas (Washington DC)
* ESRI North American locator (REST & SOAP)
* ESRI European address locator (REST & SOAP)
* MapQuest Licensed Data API
* MapQuest-hosted Nominatim Open Data API

See the source for more info.  Here's a quick example.

>>> from omgeo import Geocoder 
>>> g = Geocoder() 
>>> candidates = g.geocode('340 N 12th St, Philadelphia PA')
