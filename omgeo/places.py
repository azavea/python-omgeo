class Viewbox():
    """
    Class representing a bounding box.
    Defaults to maximum bounds for WKID 4326.
    """
    def convert_srs(self, new_wkid):
        """Return a new Viewbox object with the specified SRS."""
        return self  # not yet implemented

    def __init__(self, left=-180, top=90, right=180, bottom=-90, wkid=4326):
        """
        :arg left: Minimum X value (default ``-180``)
        :arg top: Maximum Y value (default ``90``)
        :arg right: Maximum X value (default ``180``)
        :arg bottom: Minimum Y value (default ``-90``)
        :arg wkid: Well-known ID for spatial reference system (default ``4326``)
        """
        bounds = left, right, bottom, top
        if not all([isinstance(x, (int, long, float)) for x in bounds]):
            raise ValueError('One or more bounds (%s) is not a real number.' % bounds)
        if left > right:
            raise ValueError('Left x-coord must be less than right x-coord.')
        if bottom > top:
            raise ValueError('Bottom y-coord must be less than top y-coord.')
        for k in locals().keys():
            if k != 'self':
                setattr(self, k, locals()[k])

    def to_bing_str(self):
        """
        Convert Viewbox object to a string that can be used by Bing
        as a query parameter.
        """
        vb = self.convert_srs(4326)
        return '%s,%s,%s,%s' % (vb.bottom, vb.left, vb.top, vb.right)

    def to_mapzen_dict(self):
        """
        Convert Viewbox object to a string that can be used by Mapzen
        as a query parameter.
        """
        vb = self.convert_srs(4326)
        return {
            'boundary.rect.min_lat': vb.bottom,
            'boundary.rect.min_lon': vb.left,
            'boundary.rect.max_lat': vb.top,
            'boundary.rect.max_lon': vb.right
        }

    def to_google_str(self):
        """ Convert to Google's bounds format: 'latMin,lonMin|latMax,lonMax' """
        vb = self.convert_srs(4326)
        return '%s,%s|%s,%s' % (vb.bottom, vb.left, vb.top, vb.right)

    def to_mapquest_str(self):
        """
        Convert Viewbox object to a string that can be used by
        `MapQuest <http://www.mapquestapi.com/geocoding/#options>`_
        as a query parameter.
        """
        vb = self.convert_srs(4326)
        return '%s,%s,%s,%s' % (vb.left, vb.top, vb.right, vb.bottom)

    def to_esri_wgs_json(self):
        """
        Convert Viewbox object to a JSON string that can be used
        by the ESRI World Geocoding Service as a parameter.
        """
        try:
            return ('{ "xmin" : %s, '
                    '"ymin" : %s, '
                    '"xmax" : %s, '
                    '"ymax" : %s, '
                    '"spatialReference" : {"wkid" : %d} }'
                    % (self.left,
                       self.bottom,
                       self.right,
                       self.top,
                       self.wkid))
        except ValueError:
            raise Exception('One or more values could not be cast to a number. '
                            'Four bounding points must be real numbers. '
                            'WKID must be an integer.')

    def __repr__(self):
        top = "y=%s" % self.top
        right = "x=%s" % self.right
        bottom = "y=%s" % self.bottom
        left = "x=%s" % self.left

        def lbl(str_, align='L'):
            MAX_CHARS = 8
            str_len = len(str_)
            if str_len > MAX_CHARS:
                return str_[:MAX_CHARS]
            if align == 'L':
                return str_
            num_spaces = (MAX_CHARS - str_len)  # num spaces to pad right-aligned
            if align == 'C':
                num_spaces = int(num_spaces / 2)
            padding = num_spaces * ' '
            return '%s%s' % (padding, str_)

        return    '          %s\n'\
                  '        ------------\n'\
                  '        |          |\n'\
                  '%s|          |%s\n'\
                  '        |          |\n'\
                  '        ------------\n'\
                  '          %s' % (lbl(top, 'C'), lbl(left, 'R'), lbl(right, 'L'), lbl(bottom, 'C'))


class PlaceQuery():
    """
    Class representing an address or place that will be passed to geocoders.
    """
    def __init__(self, query='', address='', neighborhood='', city='',
                 subregion='', state='', postal='', country='',
                 viewbox=None, bounded=False, **kwargs):
        """
        :arg str query: A string containing the query to parse
                        and match to a coordinate on the map.
                        *ex: "340 N 12th St Philadelphia PA 19107"
                        or "Wolf Building, Philadelphia"*
        :arg str address: A string for the street line of an address.
                          *ex: "340 N 12th St"*
        :arg str neighborhood: A string for the subdivision of a city. Not used
                               in US addresses, but used in Mexico and other places.
        :arg str city: A string specifying the populated place for the address.
                       This commonly refers to a city, but may refer to a suburb
                       or neighborhood in certain countries.
        :arg str subregion: A string for a region between the city and state level.
                            Not used in US addresses.
        :arg str state: A string for the state, province, territory, etc.
        :arg str postal: A string for the postal / ZIP Code
        :arg str country: A string for the country or region. Because the geocoder
                          uses the country to determine which geocoding service to use,
                          this is strongly recommended for efficency. ISO alpha-2 is
                          preferred, and is required by some geocoder services.
        :arg Viewbox viewbox: A Viewbox object indicating the preferred area
                              to find search results (default ``None``)
        :arg bool bounded: Boolean indicating whether or not to only
                           return candidates within the given Viewbox (default ``False``)

        :key float user_lat: A float representing the Latitude of the end-user.
        :key float user_lon: A float representing the Longitude of the end-user.
        :key str user_ip: A string representing the IP address of the end-user.
        :key str culture: Culture code to be used for the request (used by Bing).
                          For example, if set to 'de', the country for a U.S. address
                          would be returned as "Vereinigte Staaten Von Amerika"
                          instead of "United States".
    """
        for k in locals().keys():
            if k not in ['self', 'kwargs']:
                setattr(self, k, locals()[k])
        if query == '' and address == '' and city == '' and state == '' and postal == '':
            raise Exception('Must provide query or one or more of address, city, state, and postal.')
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __repr__(self):
        return '<%s%s %s>' % (self.query, self.address, self.postal)


class Candidate():
    """
    Class representing a candidate address returned from geocoders.
    Accepts arguments defined below, plus informal keyword arguments.

    Usage Example::

        c = Candidate('US_RoofTop', 91.5, '340 N 12th St, Philadelphia, PA, 19107',
            '-75.16', '39.95', some_key_foo='bar')
    """

    def __init__(self, locator='', score=0, match_addr='', x=None, y=None,
                 wkid=4326, **kwargs):
        """
        :arg locator: Locator used for geocoding (default ``''``)

                      We try to standardize this to
                       * ``rooftop``,
                       * ``interpolated``,
                       * ``postal_specific``, and
                       * ``postal``.

        :arg score: Standardized score (default ``0``)
        :arg str match_addr: Address returned by geocoder (default ``''``)
        :arg x: X-coordinate (longitude for lat-lon SRS) (default ``None``)
        :arg y: Y-coordinate (latitude for lat-lon SRS) (default ``None``)
        :arg wkid: Well-known ID for spatial reference system (default ``4326``)

        Keyword arguments can be added in order to be able to use postprocessors
        with API output fields are not well-fitted for one of the definitions
        above.

        If possible, it is suggested for geocoders to additionally return the following
        address components:
            * match_streetaddr (the street address, e.g. '340 N 12th Street')
            * match_city
            * match_subregion (county)
            * match_region (state / province)
            * match_postal
            * match_country
        However, these are not required. Currently the EsriWGS and US Census geocoders
        return these values.
        """

        for k in locals().keys():
            if k not in ['self', 'kwargs']:
                setattr(self, k, locals()[k])
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __repr__(self):
        if self.match_addr == '':
            match_addr = '(no address specified)'
        else:
            match_addr = self.match_addr

        if self.x is None:
            x = '(no x coord specified)'
        else:
            x = self.x

        if self.y is None:
            y = '(no y coord specified)'
        else:
            y = self.y

        geoservice = '%s' % getattr(self, 'geoservice', '(no geoservice specified')
        return '<%s (%s, %s) %s>' % (match_addr, x, y, geoservice)
