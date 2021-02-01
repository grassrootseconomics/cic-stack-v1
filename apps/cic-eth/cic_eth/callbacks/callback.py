# third-party imports
import celery

class Callback(celery.Task):
    """Provides static properties for web connection context. The properties should be set directly.
    """
    ssl = False
    """If true, a SSL client certificate with default protocol for standard library ssl will be used for the HTTP connection."""
    ssl_cert_file = None
    """Absolute path to client certificate PEM file"""
    ssl_key_file = None
    """Absolute path to client key file"""
    ssl_password=None
    """Password to unlock key file"""
    ssl_ca_file = None
    """Client certificate CA chain"""
