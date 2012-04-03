**The Oatmeal Geocoder - Python Edition**

``python-omgeo`` is a geocoding abstraction layer written in python.  Currently
supported geocoders:

* Bing
* ESRI's North American locator
* ESRI's European address locator
* Nominatim
* Citizen Atlas (Washington DC)


See the source for more info.  Here's a quick example.

>>> from omgeo import Geocoder 
>>> from omgeo.places import PlaceQuery  
>>> g = Geocoder() 
>>> you_are_here = PlaceQuery('340 N 12th St Philadelphia PA') 
>>> candidates = g.geocode(you_are_here)
