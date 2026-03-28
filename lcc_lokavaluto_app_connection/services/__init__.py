from . import partner_services
from . import auth_services

__api_version__ = 13


##
## Feature negotiation helpers
##


_FEATURELESS = "feature-less/0"


class MissingCommonFeature(Exception):
    """Raised when client and server share no common feature version."""

    def __init__(self, supported_features):
        self.supported_features = supported_features
        super().__init__(
            f"No common feature version. Server supports: {sorted(supported_features)}"
        )


def features_header_parse(features_string):
    """Parse a features header value into individual feature/version strings.

    Accepts space-separated feature specifiers, each in the form
    ``name/version-spec`` where version-spec is a comma-separated
    list of integers or integer ranges.

    Examples::

        >>> list(features_header_parse("search/0-2 auth/1"))
        ['search/0', 'search/1', 'search/2', 'auth/1']
        >>> list(features_header_parse("cap/0-2,5"))
        ['cap/0', 'cap/1', 'cap/2', 'cap/5']

    """

    for feature_range in features_string.split():
        name, version_specs = feature_range.split("/", 1)
        for spec in version_specs.split(","):
            if "-" in spec:
                beg, end = spec.split("-", 1)
                beg, end = int(beg), int(end)
            else:
                beg = end = int(spec)
            for version in range(beg, end + 1):
                yield f"{name}/{version}"


def features(supported_feature_string):
    """Decorator declaring the features an endpoint supports.

    Stackable: multiple ``@features`` decorators on the same
    endpoint accumulate their supported sets (union).  The
    outermost ``@features`` wrapper performs the actual
    negotiation using the full accumulated set.

    Reads ``X-Client-Features`` from the request header.  If absent,
    assumes ``feature-less/0`` (legacy behavior).  If no intersection
    exists between client and server feature sets, raises
    :class:`MissingCommonFeature`.

    The negotiated common features are stored on
    ``request._common_features`` and used features on
    ``request._used_features`` for building the
    ``X-Selected-Features`` response header.
    """
    supported = set(features_header_parse(supported_feature_string))

    def decorator(func):
        # Accumulate from inner @features decorators
        accumulated = getattr(func, "_supported_features", set()) | supported

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                is_outermost = getattr(request, "_common_features", None) is None
            except RuntimeError:
                # No active HTTP request (tests, cron, internal calls)
                return func(self, *args, **kwargs)
            if is_outermost:
                client_features = set(
                    features_header_parse(
                        request.httprequest.headers.get("X-Client-Features", "")
                    )
                )
                request.future_response.headers["X-Supported-Features"] = " ".join(
                    sorted(accumulated or {_FEATURELESS})
                )

                common = (accumulated or {_FEATURELESS}) & (
                    client_features or {_FEATURELESS}
                )
                if not common:
                    raise MissingCommonFeature(accumulated)
                request._common_features = common
                request._used_features = set()

            result = func(self, *args, **kwargs)

            if is_outermost:
                if not request._used_features:
                    real = request._common_features - {_FEATURELESS}
                    if not real:
                        use_feature(_FEATURELESS)
                    elif len(real) == 1:
                        use_feature(next(iter(real)))
                    else:
                        raise ValueError("You must use_feature at least once")
                if request._used_features:
                    if (
                        len(request._used_features) != 1
                        or next(iter(request._used_features)) != _FEATURELESS
                        or len(client_features) != 0
                    ):
                        request.future_response.headers["X-Selected-Features"] = (
                            " ".join(sorted(request._used_features))
                        )
                request._common_features = None

            return result

        wrapper._supported_features = accumulated
        return wrapper

    return decorator


def has_feature(feature):
    """Check if *feature* was negotiated for the current request."""
    return feature in request._common_features


def use_feature(feature):
    """Mark *feature* as actively used in the current response.

    Raises ``ValueError`` if *feature* was not negotiated.

    """
    if feature not in request._common_features:
        raise ValueError(
            f"Feature '{feature}' was not negotiated"
            f" (common: {sorted(request._common_features)})"
        )
    request._used_features.add(feature)
    _logger.debug(
        "%s %s: use_feature('%s')",
        request.httprequest.method,
        request.httprequest.path,
        feature,
    )


def with_feature(feature):
    """Check if *feature* is available and mark it as used if so.

    Returns ``True`` if the feature was negotiated, ``False``
    otherwise.  Convenience shorthand for
    ``has_feature`` + ``use_feature``.

    """
    if has_feature(feature):
        use_feature(feature)
        return True
    return False


##
## Auto-wrap @restapi.method with feature negotiation
##

_orig_restapi_method = restapi.method


def _features_restapi_method(routes, **kwargs):
    """Wrapper around ``restapi.method`` that auto-applies ``@features("")``.

    Any endpoint that does not already carry an explicit ``@features(...)``
    decorator (detected via ``_supported_features``) gets wrapped with
    ``features("")`` — defaulting to ``feature-less/0`` negotiation.
    """

    def decorator(func):
        if getattr(func, "_supported_features", None) is None:
            func = features("")(func)
        return _orig_restapi_method(routes, **kwargs)(func)

    return decorator


restapi.method = _features_restapi_method
