import logging
import traceback
from functools import wraps
from odoo import api, registry
from odoo.sql_db import BaseCursor

_logger = logging.getLogger(__name__)


def status(reqs):
    """Return 'todo', 'done' or 'ongoing' depending if all reqs are
    not done, all done or some done.

    reqs are boolean, True to say they are done, False to say they are not done.

    Reqs is an iterable:

        >>> status(iter([True, True, True]))
        'done'
        >>> status(iter([True, True, False]))
        'ongoing'
        >>> status(iter([False, False, False]))
        'todo'
        >>> status(iter([]))
        'done'

    """
    one = {False: False, True: False}
    for r in reqs:
        if one[r]:
            continue
        one[r] = True
        if one[not r]:
            ## then we have both at least one done and one not done
            return "ongoing"
    return "todo" if one[False] else "done"


def format_last_exception(prefix="  | "):
    """Format the last exception for display it in tests.

    This allows to raise custom exception, without loosing the context of what
    caused the problem in the first place:

    >>> def f():
    ...     raise Exception("Something terrible happened")
    >>> try:  ## doctest: +ELLIPSIS
    ...     f()
    ... except Exception:
    ...     formated_exception = format_last_exception()
    ...     raise ValueError('Oups, an error occured:\\n%s'
    ...         % formated_exception)
    Traceback (most recent call last):
    ...
    ValueError: Oups, an error occured:
      | Traceback (most recent call last):
    ...
      | Exception: Something terrible happened

    """

    return "\n".join(
        str(prefix + line) for line in traceback.format_exc().strip().split("\n")
    )


def after_commit(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        assert isinstance(self.env.cr, BaseCursor)
        dbname = self.env.cr.dbname
        context = self.env.context
        uid = self.env.uid

        @self.env.cr.postcommit.add
        def called_after():
            db_registry = registry(dbname)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                try:
                    func(self.with_env(env), *args, **kwargs)
                except Exception as e:
                    _logger.warning(
                        "Postcommit function %s failed: %s" % (func.__name__, self)
                    )
                    _logger.exception(e)

    return wrapped


def transform_backend_keys_in_currency_uris(backend_keys):
    """
    Transition function to transform currency backend keys format in currency URI format.
    TO BE REMOVED once Monujo uses backend URIs
    """
    currency_uris = []
    for backend in backend_keys:
        separator_count = backend.count("://")
        if separator_count == 1:
            # backend matches wished URI structure
            currency_uris.append(backend)
        elif separator_count == 0:
            # backend is OLD format
            engine, ident = backend.split(":", 1)
            currency_uris.append(f"{engine}://{ident}")
        else:
            raise MissingError(f"Invalid backend id {backend}")
    return currency_uris


def transform_wallet_backend_keys_in_wallet_uris(wallet_backend_keys, currency_ident):
    """
    Transition function to transform wallet backend keys format in wallet URI format.
    TO BE REMOVED once Monujo uses backend URIs
    """
    wallet_uris = []
    for backend in wallet_backend_keys:
        separator_count = backend.count("/wallet/")
        if separator_count == 1:
            # backend matches wished URI structure
            wallet_uris.append(backend)
        elif separator_count == 0:
            # backend is OLD format
            engine, ident = backend.split(":", 1)
            wallet_uris.append(f"{engine}://{currency_ident}/wallet/{ident}")
        else:
            raise MissingError(f"Invalid backend id {backend}")
    return wallet_uris
