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
        In a subclass, arguments may be formally defined to avoid the use of keywords
        (and to throw errors when bogus keyword arguments are passed)::

            def __init__(self, arg1='foo', arg2='bar')

        """
        self._init_helper(vars())
