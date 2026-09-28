#!/usr/bin/env python3
import gc
import json
import os
import shutil
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODELS_ROOT = BASE / "hayeren_offline_models"
SECRET = os.environ.get("HAYEREN_OFFLINE_SECRET", "")
PORT = int(os.environ.get("PORT", "8080"))

MODEL_SPECS = {
    "ru-hy": {"repo": "manancode/opus-mt-ru-hy-ctranslate2-android"},
    "hy-ru": {"repo": "manancode/opus-mt-hy-ru-ctranslate2-android"},
}
MODEL_FILES = ("model.bin", "config.json", "shared_vocabulary.json", "source.spm", "target.spm")


def download_file(repo, name, target):
    url = f"https://huggingface.co/{repo}/resolve/main/{name}?download=true"
    req = urllib.request.Request(url, headers={"User-Agent": "HayerenOffline/1.3"})
    with urllib.request.urlopen(req, timeout=180) as response, open(target, "wb") as f:
        shutil.copyfileobj(response, f)
    if target.stat().st_size < 50:
        raise RuntimeError(f"downloaded file too small: {repo}/{name}")


def build_models():
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    for direction, spec in MODEL_SPECS.items():
        out_dir = MODELS_ROOT / direction
        marker = out_dir / ".ready"
        if marker.exists() and (out_dir / "model.bin").exists():
            print(f"MODEL_BUILD_SKIP {direction}", flush=True)
            continue
        print(f"MODEL_BUILD_START {direction}", flush=True)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        try:
            for name in MODEL_FILES:
                path = out_dir / name
                download_file(spec["repo"], name, path)
                print(f"MODEL_FILE {direction} {name} bytes={path.stat().st_size}", flush=True)
            marker.write_text("ok\n", encoding="utf-8")
            total = sum(p.stat().st_size for p in out_dir.rglob("*") if p.is_file())
            print(f"MODEL_BUILD_DONE {direction} bytes={total}", flush=True)
        except Exception:
            shutil.rmtree(out_dir, ignore_errors=True)
            raise


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
            str(model_dir), device="cpu", compute_type="int8_float32", inter_threads=1, intra_threads=1
        )
        self.source_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "source.spm"))
        self.target_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "target.spm"))
        self.direction = direction
        print(f"MODEL_LOAD_DONE {direction}", flush=True)

    @staticmethod
    def _valid_script(text, target):
        if not text:
            return False
        if target == "hy":
            return any("Ա" <= ch <= "ֆ" or ch == "և" for ch in text)
        return any(("А" <= ch <= "я") or ch in "Ёё" for ch in text)

    @staticmethod
    def _not_pathological(text):
        words = [w.lower().strip(".,!?;:—-()[]{}\"'") for w in text.split()]
        words = [w for w in words if w]
        if not words:
            return False
        if len(words) >= 8:
            most = max(words.count(w) for w in set(words))
            if most / len(words) > 0.42:
                return False
        for n in (2, 3):
            if len(words) >= n * 4:
                grams = [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
                if grams and max(grams.count(g) for g in set(grams)) >= 4:
                    return False
        return True

    def translate(self, text, source, target):
        direction = f"{source}-{target}"
        if direction not in MODEL_SPECS:
            raise ValueError("unsupported language pair")
        with self.lock:
            self._load(direction)
            # RU->HY has two target variants in the source model (Armenian script and
            # Latin transliteration), so explicitly select standard Armenian script.
            model_input = f">>hye<< {text}" if direction == "ru-hy" else text
            source_tokens = self.source_sp.encode(model_input, out_type=str)
            # The Transformers-converted Marian checkpoint expects the source EOS token.
            if not source_tokens or source_tokens[-1] != "</s>":
                source_tokens.append("</s>")
            max_output = min(128, max(24, len(source_tokens) * 5))
            result = self.translator.translate_batch(
                [source_tokens],
                beam_size=2,
                max_decoding_length=max_output,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3,
                end_token="</s>",
            )[0]
            tokens = [t for t in result.hypotheses[0] if t not in ("<s>", "</s>")]
            out = self.target_sp.decode(tokens).strip()
            out = out.replace(">>hye<<", "").replace(">>hye_Latn<<", "").replace(">>rus<<", "").strip()
            if not self._valid_script(out, target):
                raise RuntimeError(f"invalid {target} output")
            if not self._not_pathological(out):
                raise RuntimeError("pathological repetition detected")
            return out


ENGINE = Engine()


def selftest():
    tests = [
        ("добрый день", "ru", "hy", ("բարի", "օր")),
        ("Բարի օր", "hy", "ru", ("добр", "день")),
        ("где находится железнодорожный вокзал", "ru", "hy", ("որտեղ", "կայարան")),
    ]
    results = []
    ok = True
    for text, source, target, semantic_hints in tests:
        try:
            out = ENGINE.translate(text, source, target)
            low = out.lower()
            script_ok = ENGINE._valid_script(out, target)
            quality_ok = ENGINE._not_pathological(out)
            semantic_ok = any(h in low for h in semantic_hints)
            valid = script_ok and quality_ok and semantic_ok
            results.append({"source": source, "target": target, "ok": valid, "sample": out[:160]})
            ok = ok and valid
        except Exception as exc:
            results.append({"source": source, "target": target, "ok": False, "error": str(exc)})
            ok = False
    print("OFFLINE_SELFTEST " + json.dumps({"ok": ok, "results": results}, ensure_ascii=False), flush=True)
    return ok


class Handler(BaseHTTPRequestHandler):
    server_version = "HayerenOffline/1.3"

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

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

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
