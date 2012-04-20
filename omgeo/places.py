class Viewbox():
    """
    Class representing a bounding box.
    Defaults to maximum bounds for WKID 4326.

    Arguments:
    ==========
    left    -- Minimum X value (default -180)
    top     -- Maximum Y value (default 90)
    right   -- Maximum X value (default 180)
    bottom  -- Minimum Y value (default -90)
    wkid    -- Well-known ID for spatial reference system (default 4326)
    """
    def _validate(self):
        """
        Return True if WKID is found and Viewbox is within maximum bounds.
        Return True if WKID is not found.
        Otherwise raise error.
        """
        return True #TODO: Find max bounds from WKID in PostGIS database

    def convert_srs(self, new_wkid):
        """
        Return a new Viewbox object with the specified SRS.
        """
        return self # for now

    def __init__(self, left=-180, top=90, right=180, bottom=-90, wkid=4326):
        for k in locals().keys():
            if k != 'self': setattr(self, k, locals()[k])
        self._validate() 

    def to_bing_str(self):
        """
        Convert Viewbox object to a string that can be used by Bing
        as a query parameter.
        """
        vb = self.convert_srs(4326)
        return '%s,%s,%s,%s' % (vb.bottom, vb.left, vb.top, vb.right)

    def to_mapquest_str(self):
        """
        Convert Viewbox object to a string that can be used by
        MapQuest as a query parameter.
        """
        vb = self.convert_srs(4326)
        return '%s,%s,%s,%s' % (vb.left, vb.top, vb.right, vb.bottom)
    
class PlaceQuery():
    """
    Class representing an address or place passed to geocoders.

    Arguments:
    ==========
    query       --  A string containing the query to parse
                    and match to a coordinate on the map.
                    *ex: "340 N 12th St Philadelphia PA 19107"
                    or "Wolf Building, Philadelphia"*
    address     --  A string for the street line of an address.
                    *ex: "340 N 12th St"*
    city        --  A string specifying the populated place for the address.
                    This commonly refers to a city, but may refer to a suburb
                    or neighborhood in certain countries.
    state       --  A string for the state, province, territory, etc.
    postal      --  A string for the postal / ZIP Code
    country     --  A string for the country or region. Because the geocoder
                    uses the country to determine which geocoding service to use,
                    this is strongly recommended for efficency. ISO alpha-2 is
                    preferred, and is required by some geocoder services.
    viewbox     --  A Viewbox object indicating the preferred area
                    to find search results (default None)
    bounded     --  Boolean indicating whether or not to only
                    return candidates within the given Viewbox (default False)

    Keyword Arguments:
    ==================
    user_lat    --  A float representing the Latitude of the end-user.
    user_lon    --  A float representing the Longitude of the end-user.
    user_ip     --  A string representing the IP address of the end-user.
    culture     --  Culture code to be used for the request (used by Bing).
                    For example, if set to 'de', the country for a U.S. address
                    would be returned as "Vereinigte Staaten Von Amerika"
                    instead of "United States".
    """
    def __init__(self, query='', address='', city='', state='', postal='', country='', 
                viewbox=None, bounded=False, **kwargs):
        for k in locals().keys():
            if k not in ['self', 'kwargs']: setattr(self, k, locals()[k])
        if query == '' and address == '' and city == '' and state == '' and postal == '':
            raise Exception('Must provide query or one or more of address, city, state, and postal.')
        for k in kwargs:
            setattr(self, k, kwargs[k])

class Candidate():
    """
    Class representing a candidate address returned from geocoders.
    Accepts arguments defined below, plus informal keyword arguments.

    Arguments:
    ==========
    locator     -- Locator used for geocoding (default '')
    score       -- Standardized score (default 0)
    match_addr  -- Address returned by geocoder (default '')
    x           -- X-coordinate (longitude for lat-lon SRS) (default None)
    y           -- Y-coordinate (latitude for lat-lon SRS) (default None)
    wkid        -- Well-known ID for spatial reference system (default 4326)
    entity      -- Used by Bing (default '')
    confidence  -- Used by Bing (default '')
    geoservice  -- GeocodeService used for geocoding (default '')

    Usage Example:
    ==============
    c = Candidate('US_RoofTop', 91.5, '340 N 12th St, Philadelphia, PA, 19107',
        '-75.16', '39.95', some_extra_data='yellow')
    """
    def __init__(self, locator='', score=0, match_addr='', x=None, y=None,
        wkid=4326, entity='', confidence='', **kwargs):
        for k in locals().keys():
            if k not in ['self', 'kwargs']: setattr(self, k, locals()[k])
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __unicode__(self):
        return '%s - (%s, %s) via %s' % (self.match_addr, self.x, self.y, self.locator)

    def __str__(self):
        return unicode(self).encode('utf-8')
