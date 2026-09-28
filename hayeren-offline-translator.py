#!/usr/bin/env python3
import gc
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODELS_ROOT = BASE / "hayeren_offline_models"
SECRET = os.environ.get("HAYEREN_OFFLINE_SECRET", "")
PORT = int(os.environ.get("PORT", "8080"))

MODEL_SPECS = {
    "ru-hy": {
        "url": "https://object.pouta.csc.fi/Tatoeba-MT-models/rus-hye/opus-2020-06-16.zip",
        "target_prefix": ">>hye<< ",
    },
    "hy-ru": {
        "url": "https://object.pouta.csc.fi/Tatoeba-MT-models/hye-rus/opus-2020-06-16.zip",
        "target_prefix": "",
    },
}


def build_models():
    import ctranslate2
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    for direction, spec in MODEL_SPECS.items():
        out_dir = MODELS_ROOT / direction
        marker = out_dir / ".ready"
        if marker.exists() and (out_dir / "model.bin").exists():
            print(f"MODEL_BUILD_SKIP {direction}", flush=True)
            continue
        print(f"MODEL_BUILD_START {direction}", flush=True)
        with tempfile.TemporaryDirectory(prefix=f"hayeren-{direction}-") as tmp:
            tmp_dir = Path(tmp)
            zip_path = tmp_dir / "model.zip"
            raw_dir = tmp_dir / "raw"
            raw_dir.mkdir()
            req = urllib.request.Request(spec["url"], headers={"User-Agent": "HayerenOffline/1.0"})
            with urllib.request.urlopen(req, timeout=120) as response, open(zip_path, "wb") as f:
                shutil.copyfileobj(response, f)
            print(f"MODEL_DOWNLOADED {direction} bytes={zip_path.stat().st_size}", flush=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(raw_dir)
            decoder = next(raw_dir.rglob("decoder.yml"), None)
            if decoder is None:
                raise RuntimeError(f"decoder.yml missing for {direction}")
            model_dir = decoder.parent
            if out_dir.exists():
                shutil.rmtree(out_dir)
            converter = ctranslate2.converters.OpusMTConverter(str(model_dir))
            converter.convert(str(out_dir), quantization="int8_float32", force=True)
            for name in ("source.spm", "target.spm"):
                src = model_dir / name
                if not src.exists():
                    raise RuntimeError(f"{name} missing for {direction}")
                shutil.copy2(src, out_dir / name)
            marker.write_text("ok\n", encoding="utf-8")
            print(f"MODEL_BUILD_DONE {direction} bytes={sum(p.stat().st_size for p in out_dir.rglob('*') if p.is_file())}", flush=True)


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        self.direction = None
        self.translator = None
        self.source_sp = None
        self.target_sp = None

    def _load(self, direction):
        import ctranslate2
        import sentencepiece as spm
        if self.direction == direction and self.translator is not None:
            return
        self.translator = None
        self.source_sp = None
        self.target_sp = None
        self.direction = None
        gc.collect()
        model_dir = MODELS_ROOT / direction
        if not (model_dir / ".ready").exists():
            raise RuntimeError(f"model {direction} is not ready")
        print(f"MODEL_LOAD_START {direction}", flush=True)
        self.translator = ctranslate2.Translator(
            str(model_dir),
            device="cpu",
            compute_type="int8_float32",
            inter_threads=1,
            intra_threads=1,
        )
        self.source_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "source.spm"))
        self.target_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "target.spm"))
        self.direction = direction
        print(f"MODEL_LOAD_DONE {direction}", flush=True)

    @staticmethod
    def _valid(text, target):
        if not text:
            return False
        if target == "hy":
            return any("Ա" <= ch <= "ֆ" or ch == "և" for ch in text)
        return any(("А" <= ch <= "я") or ch in "Ёё" for ch in text)

    def translate(self, text, source, target):
        direction = f"{source}-{target}"
        if direction not in MODEL_SPECS:
            raise ValueError("unsupported language pair")
        with self.lock:
            self._load(direction)
            spec = MODEL_SPECS[direction]
            candidates = []
            if spec["target_prefix"]:
                candidates.append(spec["target_prefix"] + text)
            candidates.append(text)
            if direction == "hy-ru":
                candidates.append(">>rus<< " + text)
            last = ""
            for source_text in candidates:
                source_tokens = self.source_sp.encode(source_text, out_type=str)
                result = self.translator.translate_batch(
                    [source_tokens],
                    beam_size=4,
                    max_decoding_length=256,
                    repetition_penalty=1.05,
                )[0]
                tokens = result.hypotheses[0]
                out = self.target_sp.decode(tokens).strip()
                out = out.replace(">>hye<<", "").replace(">>hye_Latn<<", "").replace(">>rus<<", "").strip()
                last = out
                if self._valid(out, target):
                    return out
            if last:
                return last
            raise RuntimeError("empty translation")


ENGINE = Engine()


def selftest():
    tests = [
        ("добрый день", "ru", "hy"),
        ("Բարի օր", "hy", "ru"),
    ]
    results = []
    ok = True
    for text, source, target in tests:
        try:
            out = ENGINE.translate(text, source, target)
            valid = ENGINE._valid(out, target)
            results.append({"source": source, "target": target, "ok": valid, "sample": out[:100]})
            ok = ok and valid
        except Exception as exc:
            results.append({"source": source, "target": target, "ok": False, "error": str(exc)})
            ok = False
    print("OFFLINE_SELFTEST " + json.dumps({"ok": ok, "results": results}, ensure_ascii=False), flush=True)
    return ok


class Handler(BaseHTTPRequestHandler):
    server_version = "HayerenOffline/1.0"

    def log_message(self, fmt, *args):
        print("HTTP " + (fmt % args), flush=True)

    def _json(self, body, status=200):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/health":
            ready = all((MODELS_ROOT / d / ".ready").exists() for d in MODEL_SPECS)
            return self._json({"ok": ready, "service": "hayeren-offline-translator", "engine": "Helsinki-NLP OPUS-MT + CTranslate2 INT8"}, 200 if ready else 503)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/translate":
            return self._json({"error": "not found"}, 404)
        if not SECRET or self.headers.get("x-hayeren-secret", "") != SECRET:
            return self._json({"error": "unauthorized"}, 401)
        try:
            length = min(int(self.headers.get("Content-Length", "0") or 0), 10000)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(body.get("text", "")).strip()
            source = str(body.get("source", "")).strip().lower()
            target = str(body.get("target", "")).strip().lower()
            if not text or len(text) > 1200 or (source, target) not in (("ru", "hy"), ("hy", "ru")):
                return self._json({"error": "invalid request"}, 400)
            started = time.time()
            translated = ENGINE.translate(text, source, target)
            elapsed_ms = round((time.time() - started) * 1000)
            return self._json({"translated": translated, "provider": "Hayeren Offline · Helsinki-NLP", "verified": False, "elapsedMs": elapsed_ms})
        except Exception as exc:
            print(f"TRANSLATE_ERROR {type(exc).__name__}: {exc}", flush=True)
            return self._json({"error": "translation failed"}, 503)


def main():
    if "--build" in sys.argv:
        build_models()
        return
    missing = [d for d in MODEL_SPECS if not (MODELS_ROOT / d / ".ready").exists()]
    if missing:
        print("Models missing at runtime; building: " + ",".join(missing), flush=True)
        build_models()
    threading.Thread(target=selftest, name="hayeren-selftest", daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"HAYEREN_OFFLINE_READY port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
