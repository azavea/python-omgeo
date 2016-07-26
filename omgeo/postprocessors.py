from omgeo.processor import _Processor
import math
from operator import attrgetter


class _PostProcessor(_Processor):
    """Takes, processes, and returns list of geocoding.places.Candidate objects."""
    def process(self, candidates):
        raise NotImplementedError(
            'PostProcessor subclasses must implement process().')

    def is_case_sensitive(self):
        try:
            return 'CS' if self.case_sensitive else 'CI'
        except ValueError:
            return 'NA'

    def is_exact(self):
        try:
            return 'EXACT_MATCH' if self.exact_match else 'INEXACT_MATCH'
        except ValueError:
            return 'NA'


class LocatorFilter(_PostProcessor):
    """
    PostProcessor used to ditch results with lousy locators.

    :arg list good_locators:  A list of locators to accept results from (default [])
    """
    def __init__(self, good_locators):
        """
        :arg list good_locators:  A list of locators to accept results from (default None)
        """
        self.good_locators = good_locators

    def process(self, candidates):
        """
        :arg list candidates: list of Candidate instances
        """
        for c in candidates[:]:
            if c.locator not in self.good_locators:
                # TODO: search string, i.e. find "EU_Street_Name" in "EU_Street_Name.GBR_StreetName"
                candidates.remove(c)

        return candidates

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.good_locators)


class LocatorSorter(_PostProcessor):
    """
    PostProcessor used to sort by locators
    """

    def __init__(self, ordered_locators):
        """
        :arg list ordered_locators: a list of :py:attr:`Candidate.locator` values
                                    placed in the desired order, such as ``rooftop``,
                                    ``interpolation``, or ``postal``.
        """
        self.ordered_locators = ordered_locators

    def process(self, unordered_candidates):
        """
        :arg list candidates: list of Candidate instances

        """
        ordered_candidates = []
        # make a new list of candidates in order of ordered_locators
        for locator in self.ordered_locators:
            for uc in unordered_candidates[:]:
                if uc.locator == locator:
                    ordered_candidates.append(uc)
                    unordered_candidates.remove(uc)
        # add all the candidates that are still left
        # (whose locator values are not in ordered_locators)
        # and return the new list
        return ordered_candidates + unordered_candidates

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.ordered_locators)


class AttrRename(_PostProcessor):
    """
    PostProcessor used to rename the given attribute, with unspecified
    attributes appearing at the end of the list.
    """

    def __init__(self, attr, attr_map=None, exact_match=False, case_sensitive=False):
        """
        :arg str attr: Name of the attribute
        :arg dict attr_map: Map of old names : new names.
        :arg bool exact_match:
        :arg bool case_sensitive:
        """
        self.attr = attr
        self.attr_map = attr_map if attr_map is not None else {}
        self.exact_match = exact_match
        self.case_sensitive = case_sensitive

    def process(self, candidates):
        """
        :arg list candidates: list of Candidate instances
        :returns: list of Candidate instances with modified values for the given attribute
        """
        def _cc(str_):  # change case
            return str_ if self.case_sensitive else str_.lower()

        new_candidates = []
        for c in candidates[:]:
            attr_val = getattr(c, self.attr)
            if self.exact_match is False and any(_cc(k) in _cc(attr_val) for k in self.attr_map):
                map_key = [k for k in self.attr_map if _cc(k) in _cc(attr_val)][0]
                map_val = self.attr_map[map_key]
                setattr(c, self.attr, map_val)
            elif _cc(attr_val) in [_cc(a) for a in self.attr_map]:
                map_key = [k for k in self.attr_map if _cc(k) == _cc(attr_val)][0]
                setattr(c, self.attr, self.attr_map[map_key])
            new_candidates.append(c)
        return new_candidates

    def __repr__(self):
        return '<%s: %s %s Map of %s (old:new): %s>' \
            % (self.__class__.__name__, self.is_exact(), self.is_case_sensitive(), self.attr, self.attr_map)


class UseHighScoreIfAtLeast(_PostProcessor):
    """
    Limit results to results with at least the given score,
    if and only if one or more results has, at least, the
    given score. If no results have at least this score,
    all of the original results are returned intact.
    """
    def __init__(self, min_score):
        self.min_score = min_score

    def process(self, candidates):
        """
        :arg list candidates: list of Candidates
        :returns: list of Candidates where score is at least min_score,
                  if and only if one or more Candidates have at least min_score.
                  Otherwise, returns original list of Candidates.
        """
        high_score_candidates = [c for c in candidates if c.score >= self.min_score]
        if high_score_candidates != []:
            return high_score_candidates
        return candidates

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.min_score)


class ScoreSorter(_PostProcessor):
    """PostProcessor class to sort :py:class:`Candidate` scores."""
    def __init__(self, reverse=True):
        """
        :arg bool reverse: indicates if the scores should be sorted in descending
                           order (e.g. 100, 90, 80, ...) (default ``True``)
        """
        self.reverse = reverse

    def process(self, candidates):
        """
        :arg list candidates: list of Candidates
        :returns: score-sorted list of Candidates
        """
        return sorted(candidates, key=attrgetter('score'), reverse=self.reverse)

    def __repr__(self):
        order = 'high to low' if self.reverse else 'low to high'
        return '<%s: %s>' % (self.__class__.__name__, order)


class AttrSorter(_PostProcessor):
    """
    PostProcessor used to sort by a the given attribute, with unspecified
    attributes appearing at the end of the list.

    :arg list ordered_values: A list of values placed in the desired order.
    :arg str attr: The attribute on which to sort.
    """

    def __init__(self, ordered_values=None, attr='locator'):
        self.ordered_values = [] if ordered_values is None else ordered_values
        self.attr = attr

    def process(self, unordered_candidates):
        ordered_candidates = []
        # make a new list of candidates in order of ordered_values
        for value in self.ordered_values:
            for uc in unordered_candidates[:]:
                if getattr(uc, self.attr) == value:
                    ordered_candidates.append(uc)
                    unordered_candidates.remove(uc)
        # add all the candidates that are still left
        # and return the new list
        return ordered_candidates + unordered_candidates

    def __repr__(self):
        return '<%s: %s sorted by %s>' % \
            (self.__class__.__name__, self.attr, self.ordered_values)


class AttrReverseSorter(_PostProcessor):
    """
    PostProcessor used to sort by the given attributes in reverse order,
    with unspecified attributes appearing at the end of the list.

    This is good to use when a list has already been defined in a script
    and you are too lazy to use the reverse() function, or don't want
    to in order to maintain more readable code.
    """

    def __init__(self, ordered_values=None, attr='locator'):
        """
        :arg list ordered_values: A list of values placed in the reverse of the desired order.
        :arg str attribute: The attribute on which to sort
        """
        self.ordered_values = [] if ordered_values is None else ordered_values
        self.attr = attr

    def process(self, unordered_candidates):
        ordered_values = self.ordered_values
        ordered_values.reverse()
        sorter = AttrSorter(ordered_values, self.attr)
        return sorter.process(unordered_candidates)

    def __repr__(self):
        return '<%s: %s reverse sorted by %s>' % \
            (self.__class__.__name__, self.attr, self.ordered_values)


class AttrMigrator(_PostProcessor):
    """
    PostProcessor used to migrate the given attribute
    to another attribute.
    """
    def __init__(self, attr_from, attr_to, attr_map=None, exact_match=False, case_sensitive=False):
        self.attr_from = attr_from
        self.attr_to = attr_to
        self.attr_map = {} if attr_map is None else attr_map
        self.exact_match = exact_match
        self.case_sensitive = case_sensitive

    def process(self, candidates):
        def _cc(str_):  # change case
            if self.case_sensitive is False:
                return str_.lower()
            return str_

        new_candidates = []
        for c in candidates[:]:
            from_val = getattr(c, self.attr_from)
            if self.exact_match is False and any(_cc(k) in _cc(from_val) for k in self.attr_map):
                map_key = [k for k in self.attr_map if _cc(k) in _cc(from_val)][0]
                map_val = self.attr_map[map_key]
                setattr(c, self.attr_to, map_val)
            elif _cc(from_val) in [_cc(a) for a in self.attr_map]:
                map_key = [k for k in self.attr_map if _cc(k) == _cc(from_val)][0]
                setattr(c, self.attr_to, self.attr_map[map_key])
            new_candidates.append(c)
        return new_candidates

    def __repr__(self):
        return '<%s: %s -> %s %s %s>' % \
            (self.__class__.__name__, self.attr_from, self.attr_to, self.is_exact(), self.is_case_sensitive())


class AttrFilter(_PostProcessor):
    """
    PostProcessor used to ditch results with unwanted attribute values.
    """

    def __init__(self, good_values=[], attr='locator', exact_match=True):
        """
        :arg list good_values: A list of values whose candidates we will
                               accept results from (default [])
        :arg string attr: The attribute type on which to filter
        :arg bool exact_match: True if attribute must match a good value exactly.
                               False if the attribute can be a substring in a
                               good value. In other words, if our Candidate
                               attribute is 'US_Rooftop' and one of the good_values
                               is 'Rooftop', we will keep this candidate.
        """
        self._init_helper(vars())

    def process(self, candidates):
        if self.exact_match is True:
            return [c for c in candidates if getattr(c, self.attr) in self.good_values]
        else:
            return [c for c in candidates if any(gv in getattr(c, self.attr)
                                                 for gv in self.good_values)]

    def __repr__(self):
        return '<%s: %s %s in %s>' % \
            (self.__class__.__name__, self.is_exact(), self.attr, self.good_values)


class AttrExclude(_PostProcessor):
    """
    PostProcessor used to ditch results with unwanted attribute values.
    """

    def __init__(self, bad_values=[], attr='locator', exact_match=True):
        """
        :arg list bad_values: A list of values whose candidates we will
                              not accept results from (default [])
        :arg string attr: The attribute type on which to filter
        :arg bool exact_match: True if attribute must match a bad value exactly.
                               False if the bad value can be a substring of the
                               attribute value. In other words, if our Candidate
                               attribute is 'Postcode3' and one of the bad values
                               is 'Postcode' because we want something more precise,
                               like 'Address', we will not keep this candidate.
        """
        self._init_helper(vars())

    def process(self, candidates):
        if self.exact_match is True:
            return [c for c in candidates if getattr(c, self.attr) not in self.bad_values]
        else:
            return [c for c in candidates if not any(bv in getattr(c, self.attr) for bv in self.bad_values)]

    def __repr__(self):
        return '<%s: %s %s in %s>' % \
            (self.__class__.__name__, self.is_exact(), self.attr, self.bad_values)


class DupePicker(_PostProcessor):
    """
    PostProcessor used to choose the best candidate(s)
    where there are duplicates (or more than one result
    that is very similar*) among high-scoring candidates,
    such as an address.

    * When comparing attribute values, case and commas do not count.

    Usage Example:

    ================ ===== =======
    match_addr       score locator
    ================ ===== =======
    123 N Wood St    90    roof
    123 S Wood St    90    address
    123 N WOOD ST    77    address
    123, S Wood ST   85    roof
    ================ ===== =======

    Above, the first two results have the highest scores. We could just
    use those, because one of the two likely has the correct address.
    However, the second result does not have the most precise location
    for 123 S. Wood Street. While the fourth result does not score as
    high as the first two, its locator method is more desirable.
    Since the addresses are the same, we can assume that the fourth result
    will provide better data than the second.

    We can get a narrowed list as described above by running the process()
    method in the DupePicker() PostProcessor class as follows, assuming
    that the "candidates" is our list of candidates::

        dp = DupePicker(
            attr_dupes='match_addr',
            attr_sort='locator',
            ordered_list=['rooftop', 'address_point', 'address_range'])

        return dp.process(candidates)

    Output:

    ================ ===== =======
    match_addr       score locator
    ---------------- ----- -------
    123 N Wood St    90    roof
    123, S Wood ST   85    roof
    ================ ===== =======

    Output with return_clean=True:

    ================ ===== =======
    match_addr       score locator
    ---------------- ----- -------
    123 N WOOD ST    90    roof
    123 S WOOD ST    85    roof
    ================ ===== =======
    """

    def __init__(self, attr_dupes, attr_sort, ordered_list, return_clean=False):
        """
        :arg str attr_dupes: Property on which to look for duplicates.
        :arg str attr_sort: Property on which to sort using ordered_list
        :arg list ordered_list: A list of property values, from most desirable
                                to least desirable.
        :arg bool return_clean: Boolean indicating whether or not to
                                homogenize string values into uppercase
                                without commas.

        """
        self._init_helper(vars())

    def process(self, candidates):
        def cleanup(str_):
            """Returns string in uppercase and free of commas."""
            if type(str_) in [str, unicode]:
                return str_.replace(',', '').upper()
            return str_

        # if there are no candidates, then there is nothing to do here
        if candidates == []:
            return []
        hi_score = ScoreSorter().process(candidates)[0].score
        hi_score_candidates = AttrFilter([hi_score], 'score').process(candidates)
        new_candidates = []
        for hsc in hi_score_candidates:
            # get candidates with same address, including the current one:
            attr_match = self.attr_dupes
            attr_match_test_val = cleanup(getattr(hsc, attr_match))
            # make a list of candidates that have essentially the same value for attr_match (like 123 Main & 123 MAIN)
            #import IPython; IPython.embed()
            matching_candidates = [mc for mc in candidates if cleanup(getattr(mc, attr_match)) == attr_match_test_val]
            # sort them in the desired order so the first one has the best attribute value
            matching_candidates = AttrSorter(self.ordered_list, self.attr_sort).process(matching_candidates)
            # the best value available can be grabbed from the top result:
            best_attr_value = getattr(matching_candidates[0], attr_match)
            # now we can filter results that have best_attr_value:
            new_candidates_queue = AttrFilter([best_attr_value], attr_match).process(matching_candidates)
            # and append each one to our list of new candidates, if it's not there already:
            for nc in [nc for nc in new_candidates_queue if nc not in new_candidates]:
                if self.return_clean:
                    new_candidates.append(cleanup(nc))
                else:
                    new_candidates.append(nc)
        return new_candidates

    def __repr__(self):
        repr_ = '%s: SORT BY %s %s -> GROUP BY %s' % \
            (self.__class__.__name__, self.attr_sort, self.ordered_list, self.attr_dupes)
        if self.return_clean:
            repr_ += ' -> CLEAN'
        return '<%s>' % repr_


class GroupBy(_PostProcessor):
    """
    Groups results by a certain attribute by choosing the
    first occurrence in the list (this means you will want
    to sort ahead of time).


    attr   --  The attribute on which to combine results
               or a list or tuple of attributes where all
               attributes must match between candidates.
    """

    def __init__(self, attr='match_addr'):
        self._init_helper(vars())

    def process(self, candidates):
        if type(self.attr) in (tuple, list):
            return GroupByMultiple(attrs=self.attr).process(candidates)
        keepers = []
        for c_from_all in candidates[:]:
            matches = [c for c in candidates if getattr(c, self.attr) == getattr(c_from_all, self.attr)]
            if matches != []:
                keepers.append(matches[0])
                for m in matches:
                    candidates.remove(m)
        return keepers

    def __repr__(self):
        return '<%s: %s>' % \
            (self.__class__.__name__, self.attr)


class GroupByMultiple(_PostProcessor):
    """
    Groups results by a certain attribute by choosing the
    first occurrence in the list of candidates
    (this means you will want to sort ahead of time).


    attrs   --  A list or tuple of attributes on which to combine results
    """

    def __init__(self, attrs):
        self._init_helper(vars())

    def process(self, candidates):
        keepers = []
        for c_from_all in candidates[:]:
            matches = [c for c in candidates
                       if all([getattr(c, attr) == getattr(c_from_all, attr)
                               for attr in self.attrs])]
            if matches != []:
                keepers.append(matches[0])
                for m in matches:
                    candidates.remove(m)
        return keepers

    def __repr__(self):
        return '<%s: %s>' % \
            (self.__class__.__name__, self.attrs)


class SnapPoints(_PostProcessor):
    """
    Chooses the first of two or more points where they are within the given
    sphere-based great circle distance.
    """
    def __init__(self, distance=50):
        """
        :arg distance: maximum distance (in metres) between two points in which
                       the the first will be kept and the second thrown out
                       (default 50).
        """
        self.distance = distance

    def _get_distance(self, pnt1, pnt2):
        """Get distance in meters between two lat/long points"""
        lat1, lon1 = pnt1
        lat2, lon2 = pnt2
        radius = 6356752  # km
        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = radius * c
        return d

    def _points_within_distance(self, pnt1, pnt2):
        """Returns true if lat/lon points are within given distance in metres."""
        if self._get_distance(pnt1, pnt2) <= self.distance:
            return True
        return False

    def process(self, candidates):
        keepers = []
        for c_from_all in candidates[:]:
            matches = [c for c in candidates if
                       self._points_within_distance((c_from_all.x, c_from_all.y), (c.x, c.y))]
            if matches != []:
                keepers.append(matches[0])
                for m in matches:
                    candidates.remove(m)
        return keepers

    def __repr__(self):
        return '<%s: distance=%sm>' % \
            (self.__class__.__name__, self.distance)
