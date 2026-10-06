"""Medicion aislada de un modelo de voz a texto. Se ejecuta en un subproceso.

Uso: python -m actaflow_engine.diagnostico.medir --modelo-dir DIR --audio WAV [--spacy NOMBRE]

Imprime una sola linea JSON en stdout. Se corre en un proceso aparte para que la memoria
pico medida sea solo la de este modelo y para que, si el sistema mata el proceso por falta
de memoria, el motor principal siga vivo y pueda informarlo.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time


def _rss_pico_bytes() -> int:
    # En Linux ru_maxrss viene en kilobytes.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def medir(modelo_dir: str, audio: str, spacy_modelo: str | None) -> dict[str, object]:
    inicio_import = time.perf_counter()
    from faster_whisper import WhisperModel

    import_s = time.perf_counter() - inicio_import

    inicio_carga = time.perf_counter()
    modelo = WhisperModel(
        modelo_dir, device="cpu", compute_type="int8", cpu_threads=1, num_workers=1
    )
    carga_s = time.perf_counter() - inicio_carga
    rss_tras_carga = _rss_pico_bytes()

    inicio_tx = time.perf_counter()
    segmentos, info = modelo.transcribe(
        audio,
        language="es",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    transcripcion_s = time.perf_counter() - inicio_tx
    rss_tras_transcripcion = _rss_pico_bytes()

    duracion_audio_s = float(info.duration)
    resultado: dict[str, object] = {
        "import_s": round(import_s, 3),
        "carga_s": round(carga_s, 3),
        "transcripcion_s": round(transcripcion_s, 3),
        "duracion_audio_s": round(duracion_audio_s, 3),
        "factor_tiempo_real": round(transcripcion_s / duracion_audio_s, 3)
        if duracion_audio_s > 0
        else None,
        "rss_tras_carga_bytes": rss_tras_carga,
        "rss_tras_transcripcion_bytes": rss_tras_transcripcion,
        "texto": texto,
    }

    if spacy_modelo:
        import spacy

        inicio_nlp = time.perf_counter()
        nlp = spacy.load(spacy_modelo)
        nlp(texto or "Prueba de carga del modelo.")
        resultado["spacy_modelo"] = spacy_modelo
        resultado["spacy_carga_s"] = round(time.perf_counter() - inicio_nlp, 3)

    resultado["rss_pico_bytes"] = _rss_pico_bytes()
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo-dir", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--spacy", default=None)
    args = parser.parse_args(argv)
    print(json.dumps(medir(args.modelo_dir, args.audio, args.spacy), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
