"""Capa gRPC del motor: servidor nativo (HTTP/2) y pasarela gRPC-Web (HTTP/1.1)."""

# Metadato que la pasarela gRPC-Web agrega al reenviar, para que los servicios sepan por
# que transporte llego la llamada (se muestra en la pagina /estado).
METADATO_TRANSPORTE = "x-actaflow-transport"
TRANSPORTE_GRPC_WEB = "grpc-web"
