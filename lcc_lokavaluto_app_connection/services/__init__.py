import functools
import inspect
import logging
from urllib.parse import unquote, urlparse

from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.base_rest import restapi

from . import gate
from .gate import (
    ADMIN_ACTIONS,
    ANY_ADMIN_ACTION,
    And,
    GateContext,
    GateLit,
    Not,
    Or,
    Self,
)


__api_version__ = 13

_logger = logging.getLogger(__name__)


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


##
## Currency API decorator
##


def _parse_caller_ident(user_uri):
    """Extract the ident portion of a ``user_uri`` header value.

    Expected shape: ``<scheme>://<currency>/user/<ident>``.

    Backend-agnostic: every backend publishing a wallet service MUST
    follow the ``/user/<ident>`` path convention.  A URI that does
    not match is a structural error — the caller sent a malformed
    or out-of-convention URI.  This function raises so the decorator
    can fail the request loudly instead of silently degrading.

    Args:
        user_uri: non-empty value of the ``X-Lokapi-Caller-User-Uri``
            header.  Must already have been checked for truthiness
            by the caller.

    Returns:
        str: URL-decoded caller ident (e.g. ``"0xabc"``).

    Raises:
        ValueError: on any structural mismatch (bad URL syntax,
            missing ``/user/`` segment, empty ident, etc.).  The
            message embeds ``user_uri`` for diagnostics.
    """
    try:
        parsed = urlparse(user_uri)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Malformed caller user_uri (urlparse failed): {user_uri!r}"
        ) from exc
    ## parsed.path looks like "/user/<ident>" — drop the leading "/"
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2 or parts[0] != "user":
        raise ValueError(
            f"Malformed caller user_uri (expected '/user/<ident>' path): {user_uri!r}"
        )
    ident = parts[1]
    if not ident:
        raise ValueError(f"Malformed caller user_uri (empty ident): {user_uri!r}")
    ## Normalise URL-encoding so it matches the target wallet_ident
    ## which the decorator also unquotes before ``SELF`` comparison.
    return unquote(ident)


def lcc_api(routes, require_actions=None, **kwargs):
    """Like ``@restapi.method`` but auto-validates ``X-Lokapi-Caller-User-Uri``.

    Reads the ``X-Lokapi-Caller-User-Uri`` HTTP header, parses the
    caller's ident, and delegates authentication to
    ``self._auth_user_uri(user_uri)`` which each backend overrides.
    Gates access using an explicit action-expression DSL — see
    :mod:`.gate`.

    Args:
        routes: Same as ``@restapi.method`` routes parameter.
        require_actions: Action gate.  Either ``None`` (no gate — any
            authenticated caller passes) or any value accepted by
            :class:`~.gate.And` (a string, a :class:`~.gate.GateExpr`,
            or one of each).  The value is wrapped in
            :class:`~.gate.And` and evaluated against a
            :class:`~.gate.GateContext` built from the caller's
            actions, ident, and the ``wallet_ident`` URL parameter
            (if any).
        **kwargs: Passed through to ``@restapi.method``.

    Raises:
        TypeError: if ``require_actions`` is not a valid operand for
            :class:`~.gate.And`, or if the gate uses :class:`~.gate.Self`
            but the wrapped endpoint does not accept a ``wallet_ident``
            parameter.
    """
    gate_expr = None if require_actions is None else And(require_actions)

    def decorator(func):
        # -- Inspect the wrapped function's signature --
        sig = inspect.signature(func)
        has_target_param = "wallet_ident" in sig.parameters

        # -- Decoration-time validation --
        if gate_expr is not None and gate_expr.needs_target:
            if not has_target_param:
                raise TypeError(
                    f"@lcc_api gate for {func.__qualname__!r} uses "
                    f"``SELF`` but the endpoint has no 'wallet_ident' "
                    f"parameter: {gate_expr!r}"
                )

        @functools.wraps(func)
        def wrapper(self, *args, **kw):
            # -- Read header --
            caller_user_uri = request.httprequest.headers.get(
                "X-Lokapi-Caller-User-Uri"
            )
            if not caller_user_uri:
                _logger.debug("lcc_api: missing X-Lokapi-Caller-User-Uri header")
                raise AccessDenied()

            # -- Parse caller ident (backend-agnostic; fail-early) --
            try:
                caller_wallet_ident = _parse_caller_ident(caller_user_uri)
            except ValueError as exc:
                _logger.warning("lcc_api: %s", exc)
                raise AccessDenied()

            # -- Delegate auth to backend --
            caller_actions = self._auth_user_uri(caller_user_uri)

            # -- Build gate context & evaluate --
            if gate_expr is not None:
                ## Bind positional + keyword args to parameters so the
                ## gate sees ``wallet_ident`` whether it was passed
                ## positionally or as a kwarg.
                target_raw = None
                if has_target_param:
                    try:
                        bound = sig.bind(self, *args, **kw)
                        target_raw = bound.arguments.get("wallet_ident")
                    except TypeError:
                        ## Signature mismatch — leave target_raw None
                        ## and let the gate reject if it needs target.
                        target_raw = None
                target_ident = unquote(target_raw) if target_raw is not None else None
                ctx = GateContext(
                    caller_actions=frozenset(caller_actions or ()),
                    caller_wallet_ident=caller_wallet_ident,
                    target_wallet_ident=target_ident,
                )
                if not gate_expr.matches(ctx):
                    _logger.debug(
                        "lcc_api: caller ident=%r actions=%s "
                        "target=%r do not satisfy gate %r",
                        caller_wallet_ident,
                        sorted(caller_actions or ()),
                        ctx.target_wallet_ident,
                        gate_expr,
                    )
                    raise AccessDenied()

            return func(self, *args, **kw)

        return restapi.method(routes, **kwargs)(wrapper)

    return decorator


from . import partner_services  # noqa: E402
from . import lccapi_services  # noqa: E402
from . import wallet_services  # noqa: E402
from . import recipient_services  # noqa: E402
from . import auth_services  # noqa: E402
from . import payment_request_services  # noqa: E402
from . import payment_request_recurrent_contract_services  # noqa: E402
