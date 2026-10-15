"""ActaFlow - motor de voz a texto y extraccion de entidades juridicas."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Una sola fuente de verdad: la version declarada en pyproject.toml.
    __version__ = version("actaflow-engine")
except PackageNotFoundError:  # pragma: no cover - solo si se ejecuta sin instalar el paquete
    __version__ = "0.0.0+sin-instalar"
