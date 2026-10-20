"""Genera la clave privada del motor (ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY).

    python -m actaflow_engine.herramientas.clave_procesador

Imprime la clave (PKCS#8 en base64url) y su huella. Usa una distinta en local y en produccion, y
guardala solo como variable de entorno: nunca en un archivo del repositorio.
"""

from __future__ import annotations

from actaflow_engine.seguridad.procesador import ClaveProcesador


def main() -> None:
    clave = ClaveProcesador.nueva()
    print(clave.pkcs8_base64url())
    print(f"huella: {clave.huella}")


if __name__ == "__main__":
    main()
