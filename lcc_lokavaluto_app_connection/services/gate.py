"""Action-gate expression DSL for ``@lcc_api`` endpoints.

Expressions are predicates over a :class:`GateContext` that carries:

- ``caller_actions`` — actions held by the authenticated caller
- ``caller_wallet_ident`` — the ident parsed from the caller's URI
- ``target_wallet_ident`` — the ``wallet_ident`` URL parameter, if any

Available expression types:

- :class:`GateLit` — matches when a specific action string is held.
- :class:`Not` — inverts an expression.
- :class:`Or` — any of the sub-expressions match.
- :class:`And` — every sub-expression matches.
- :class:`Self` — caller's ident equals target's ident.  Requires the
  endpoint to accept a ``wallet_ident`` parameter; misuse on a
  targetless endpoint is detected at decoration time (see
  :func:`services.lcc_api`).

Concrete expression classes inherit from :class:`GateOp` which
factorises operand storage, arity enforcement, ``needs_target``
propagation, and ``__repr__``.  Subclasses mostly just declare
``arity`` and implement ``matches``.

Composition uses Python operators:

- ``a | b`` — ``Or(a, b)`` (caller matches either)
- ``a & b`` — ``And(a, b)`` (caller matches both)
- ``~a``   — ``Not(a)``

Where an operand would be a ``str``, it is auto-wrapped to
:class:`GateLit` by :class:`GateOp`.  So ``Or("activate", SELF)`` and
``Or(GateLit("activate"), SELF)`` are equivalent.  The canonical
"caller is self OR caller is admin" gate reads
``SELF | ANY_ADMIN_ACTION``.

Design contract:

- Expressions are pure predicates over a context snapshot.  They must
  not mutate state or read external systems.
- Expressions must never take ``self.env`` or similar globals.  All
  state they examine must be pre-computed on the :class:`GateContext`.
- ``__repr__`` returns a source-like rendering for log messages and
  debugger output; action literals render with quotes so the output
  is structurally valid Python (e.g. ``Or('a', 'b')``, ``Self()``,
  ``Or(Self(), 'activate')``).  Intentionally evaluation-friendly but
  not a canonical serialisation — do not rely on ``eval()``
  round-tripping.
- Operand order is preserved in storage and repr (insertion order).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GateContext:
    """Immutable snapshot of request state for gate evaluation.

    Attributes:
        caller_actions: Actions held by the authenticated caller
            (from ``_auth_user_uri()``).
        caller_wallet_ident: Ident portion of the caller's ``user_uri``
            (the part after ``/user/``).  ``None`` if the URI was
            malformed or absent.
        target_wallet_ident: Value of the ``wallet_ident`` URL
            parameter, if the endpoint accepts one.  ``None`` on
            targetless endpoints.
    """

    caller_actions: frozenset = field(default_factory=frozenset)
    caller_wallet_ident: str = None
    target_wallet_ident: str = None


class GateExpr:
    """Top-level base for gate expressions.

    Holds the operator sugar (``|``, ``&``, ``~``) shared by all
    expression types.  Custom expression classes should typically
    inherit from :class:`GateOp` (which already implements storage,
    validation, and repr) rather than from ``GateExpr`` directly.
    """

    def matches(self, ctx):
        """Return ``True`` if *ctx* satisfies the expression.

        Args:
            ctx: :class:`GateContext` built by the decorator.

        Returns:
            bool.
        """
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError

    @property
    def needs_target(self):
        """``True`` if the expression references the target wallet.

        Used by the ``@lcc_api`` decorator to detect misuse at import
        time (e.g. ``SELF`` on an endpoint without ``wallet_ident``).
        """
        return False

    ## Operator sugar: a | b, a & b, ~a — values are passed through
    ## to the constructor, which handles str → GateLit wrapping.

    def __or__(self, other):
        return Or(self, other)

    def __ror__(self, other):
        return Or(other, self)

    def __and__(self, other):
        return And(self, other)

    def __rand__(self, other):
        return And(other, self)

    def __invert__(self):
        return Not(self)


class GateOp(GateExpr):
    """Abstract base for all concrete gate operations.

    Every concrete gate class is an operation with an :attr:`arity`
    (``0``, ``1``, or ``None`` for unlimited/variadic).  All operands
    are :class:`GateExpr` instances after construction; any ``str``
    passed to :meth:`__init__` is auto-wrapped to :class:`GateLit`
    transparently.  Subclasses declare :attr:`arity` and implement
    :meth:`matches`.
    """

    arity = None  ## int = exact arity; None = variadic

    def __init__(self, *operands):
        cls_name = type(self).__name__
        wrapped = []
        for op in operands:
            if isinstance(op, str):
                wrapped.append(GateLit(op))
            elif isinstance(op, GateExpr):
                wrapped.append(op)
            else:
                raise TypeError(
                    f"{cls_name}() operands must be GateExpr (or str, "
                    f"auto-wrapped to GateLit), got: "
                    f"{type(op).__name__} ({op!r})"
                )
        if self.arity is not None and len(wrapped) != self.arity:
            raise TypeError(
                f"{cls_name}() takes exactly {self.arity} operand(s), "
                f"got {len(wrapped)}"
            )
        self._operands = tuple(wrapped)

    @property
    def needs_target(self):
        ## Default: propagate through operands.  Nullary ops default
        ## to False; :class:`Self` overrides to True.
        return any(op.needs_target for op in self._operands)

    def __repr__(self):
        return f"{type(self).__name__}({', '.join(repr(op) for op in self._operands)})"


##
## Leaves (nullary operations, no operands)
##


class GateLit(GateExpr):
    """Match when a specific action string is held by the caller.

    ``GateLit("activate")`` matches if ``"activate"`` is in
    ``ctx.caller_actions``.

    Strings passed to any :class:`GateOp` constructor are auto-wrapped
    to ``GateLit``, so ``Or("activate", SELF)`` works transparently
    and :class:`GateLit` rarely needs to be used explicitly.

    ``GateLit`` is a leaf — it wraps a raw string, not a
    :class:`GateExpr` operand — so it inherits directly from
    :class:`GateExpr` rather than :class:`GateOp`.
    """

    def __init__(self, action):
        if not isinstance(action, str):
            raise TypeError(
                f"GateLit() action must be a str, got: "
                f"{type(action).__name__} ({action!r})"
            )
        self._action = action

    def matches(self, ctx):
        return self._action in ctx.caller_actions

    def __repr__(self):
        return repr(self._action)


class Self(GateOp):
    """Match when the caller targets their own wallet.

    Compares ``caller_wallet_ident`` with ``target_wallet_ident``.  A
    missing target or missing caller yields ``False``.

    Must only appear in gates on endpoints that accept a
    ``wallet_ident`` parameter.  The ``@lcc_api`` decorator validates
    this at decoration time and raises :class:`TypeError` on misuse.

    ``Self`` takes no arguments and carries no state; prefer the
    module-level :data:`SELF` singleton over instantiating this class
    directly.
    """

    arity = 0

    def matches(self, ctx):
        if ctx.caller_wallet_ident is None:
            return False
        if ctx.target_wallet_ident is None:
            return False
        return ctx.caller_wallet_ident == ctx.target_wallet_ident

    @property
    def needs_target(self):
        return True


##
## Unary operations
##


class Not(GateOp):
    """Invert an inner expression.

    ``Not("reconvert")`` passes when the caller does NOT hold the
    ``reconvert`` action (the string auto-wraps to ``GateLit``).
    """

    arity = 1

    def matches(self, ctx):
        return not self._operands[0].matches(ctx)


##
## Variadic operations
##


class Or(GateOp):
    """Match if ANY of the sub-expressions match.

    ``Or("activate", "search-all-recipients")`` (strings auto-wrap to
    :class:`GateLit`) — the classic "any of these actions" gate.
    """

    def matches(self, ctx):
        return any(op.matches(ctx) for op in self._operands)


class And(GateOp):
    """Match only if EVERY sub-expression matches.

    An empty ``And()`` always matches (vacuous truth).
    """

    def matches(self, ctx):
        return all(op.matches(ctx) for op in self._operands)


##
## Convenience constants
##


##: Set of admin-role actions currently defined in the codebase.
## Used by endpoints that accept any admin caller.  Update this when
## a new admin action is introduced; endpoints using
## ``ANY_ADMIN_ACTION`` pick it up automatically.
ADMIN_ACTIONS = (
    "activate",
    "search-all-recipients",
    "validate-credit-request",
)

##: Gate accepting any admin caller (holds at least one admin action).
ANY_ADMIN_ACTION = Or(*ADMIN_ACTIONS)

##: Subset of admin actions that imply broad administrative authority
## over wallet metadata (create/edit/archive/view arbitrary wallet
## info).  Narrower than ``ANY_ADMIN_ACTION``: excludes
## ``validate-credit-request``, whose holders have authority scoped
## to credit-request validation, not general wallet administration.
WALLET_ADMIN_ACTIONS = (
    "activate",
    "search-all-recipients",
)

##: Gate accepting wallet-administrator callers.  Excludes roles whose
## only admin action is ``validate-credit-request``.
WALLET_ADMIN = Or(*WALLET_ADMIN_ACTIONS)

##: Singleton :class:`Self` instance.  Prefer this over instantiating
## :class:`Self` per endpoint — no state, no reason to re-create.
SELF = Self()
