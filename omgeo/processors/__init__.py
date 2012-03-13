class _Processor():
    def _init_helper(self, vars_):
        """Overwrite defaults (if they exist) with arguments passed to constructor"""      
        for k in vars_:
            if k == 'kwargs':
                for kwarg in vars_[k]:
                    setattr(self, kwarg, vars_[k][kwarg])
            elif k != 'self':
                setattr(self, k, vars_[k])

    def __init__(self, **kwargs):
        """
        Constructor for Processor.
        
        In a subclass, arguments may be formally defined to avoid the use of keywords
        (and to throw errors when bogus keyword arguments are passed):

            def __init__(self, arg1='foo', arg2='bar')
        """
        self._init_helper(vars())

class PreProcessor(_Processor):
    """Takes, processes, and returns a geocoding.places.PlaceQuery object."""
    def process(self, pq):
        raise NotImplementedError(
            'PreProcessor subclasses must implement process().')

class PostProcessor(_Processor):
    """Takes, processes, and returns list of geocoding.places.Candidate objects."""
    def process(self, candidates):
        raise NotImplementedError(
            'PostProcessor subclasses must implement process().')
