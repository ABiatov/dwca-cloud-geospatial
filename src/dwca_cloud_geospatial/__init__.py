"""Core package for the DwC-A cloud geospatial converter."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dwca-cloud-geospatial")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
