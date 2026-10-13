"""Validation and URL helpers for survey completion messages."""

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

OPTION_KEYS = ("parent_origin", "return_label")


def completion_email(value):
    """Return a bounded email suggestion, never an arbitrary mapped text answer."""
    if not isinstance(value, str):
        return None
    email = value.strip()
    if (
        len(email) > 254
        or re.search(r"[\x00-\x1f\x7f]", email)
        or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
    ):
        return None
    return email


def origin(url):
    """Return a canonical HTTP(S) origin, rejecting ambiguous browser URLs."""
    if not isinstance(url, str) or re.search(r"[\s\\\x00-\x1f\x7f]", url):
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            return None
        hostname = parts.hostname.encode("idna").decode("ascii").lower()
        if ":" in hostname:
            hostname = f"[{ipaddress.IPv6Address(hostname)}]"
        elif not re.fullmatch(r"[a-z0-9.-]+", hostname):
            return None
        port = parts.port
        if port is not None and port != (443 if parts.scheme == "https" else 80):
            hostname = f"{hostname}:{port}"
        return f"{parts.scheme}://{hostname}"
    except (ValueError, UnicodeError):
        return None


def completion_options(values):
    """Keep only bounded, explicit completion options; never copy answer tokens."""
    if not values.get("parent_origin"):
        return {}
    options = {}
    for key in OPTION_KEYS:
        if hasattr(values, "getlist") and len(values.getlist(key)) > 1:
            return {}
        value = values.get(key)
        if value is not None:
            if not isinstance(value, str) or len(value) > (120 if key == "return_label" else 4096):
                return {}
            options[key] = value
    return options


def with_query(url, values):
    """Replace named query values while preserving other pairs and the fragment."""
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in values
    ]
    query.extend(values.items())
    return urlunsplit(parts._replace(query=urlencode(query)))
