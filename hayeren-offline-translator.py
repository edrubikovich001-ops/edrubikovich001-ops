#!/usr/bin/env python3
import gc
import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.request
from collections import OrderedDict
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
    req = urllib.request.Request(url, headers={"User-Agent": "HayerenOffline/1.5"})
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


class DirectionEngine:
    def __init__(self, direction):
        import ctranslate2
        import sentencepiece as spm
        model_dir = MODELS_ROOT / direction
        if not (model_dir / ".ready").exists():
            raise RuntimeError(f"model {direction} is not ready")
        print(f"MODEL_LOAD_START {direction}", flush=True)
        self.direction = direction
        self.translator = ctranslate2.Translator(
            str(model_dir), device="cpu", compute_type="int8_float32",
            inter_threads=1, intra_threads=1
        )
        self.source_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "source.spm"))
        self.target_sp = spm.SentencePieceProcessor(model_file=str(model_dir / "target.spm"))
        print(f"MODEL_LOAD_DONE {direction}", flush=True)

    def encode(self, text):
        pieces = self.source_sp.encode(text, out_type=str)
        if self.direction == "ru-hy":
            pieces = [">>hye<<"] + pieces
        if not pieces or pieces[-1] != "</s>":
            pieces.append("</s>")
        return pieces

    def translate_one(self, text):
        source_tokens = self.encode(text)
        max_output = min(180, max(24, len(source_tokens) * 4))
        result = self.translator.translate_batch(
            [source_tokens],
            beam_size=4,
            max_decoding_length=max_output,
            repetition_penalty=1.08,
            no_repeat_ngram_size=3,
        )[0]
        tokens = [t for t in result.hypotheses[0] if t not in ("<s>", "</s>")]
        out = self.target_sp.decode(tokens).strip()
        return out.replace(">>hye<<", "").replace(">>hye_Latn<<", "").replace(">>rus<<", "").strip()


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        self.engines = {}
        self.cache = OrderedDict()
        self.cache_max = 1200

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

    @staticmethod
    def _chunks(text, max_chars=300):
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) <= max_chars:
            return [text]
        sentences = [x.strip() for x in re.split(r"(?<=[.!?։])\s+", text) if x.strip()]
        chunks, current = [], ""
        for sentence in sentences:
            if len(sentence) <= max_chars:
                candidate = (current + " " + sentence).strip()
                if current and len(candidate) > max_chars:
                    chunks.append(current)
                    current = sentence
                else:
                    current = candidate
                continue
            if current:
                chunks.append(current)
                current = ""
            words = sentence.split()
            part = ""
            for word in words:
                candidate = (part + " " + word).strip()
                if part and len(candidate) > max_chars:
                    chunks.append(part)
                    part = word
                else:
                    part = candidate
            if part:
                chunks.append(part)
        if current:
            chunks.append(current)
        return chunks or [text]

    def _get(self, direction):
        if direction not in self.engines:
            self.engines[direction] = DirectionEngine(direction)
        return self.engines[direction]

    def _cache_get(self, key):
        value = self.cache.get(key)
        if value is not None:
            self.cache.move_to_end(key)
        return value

    def _cache_put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        while len(self.cache) > self.cache_max:
            self.cache.popitem(last=False)

    def preload(self):
        with self.lock:
            for direction in MODEL_SPECS:
                self._get(direction)
        gc.collect()

    def translate(self, text, source, target):
        direction = f"{source}-{target}"
        if direction not in MODEL_SPECS:
            raise ValueError("unsupported language pair")
        key = direction + "|" + re.sub(r"\s+", " ", text).strip().lower()
        with self.lock:
            cached = self._cache_get(key)
            if cached:
                return cached
            engine = self._get(direction)
            outs = []
            for chunk in self._chunks(text):
                out = engine.translate_one(chunk)
                if not self._valid_script(out, target):
                    raise RuntimeError(f"invalid {target} output")
                if not self._not_pathological(out):
                    raise RuntimeError("pathological repetition detected")
                outs.append(out)
            translated = " ".join(x for x in outs if x).strip()
            if not translated:
                raise RuntimeError("empty translation")
            self._cache_put(key, translated)
            return translated


ENGINE = Engine()


def selftest():
    tests = [
        ("тигр", "ru", "hy", ("վագր",)),
        ("Вագր", "hy", "ru", ("тигр",)),
        ("добрый день", "ru", "hy", ("բարի", "օր")),
        ("спасибо", "ru", "hy", ("շնորհ",)),
        ("где находится железнодорожный вокзал", "ru", "hy", ("կայարան",)),
        ("Где находится ближайшая аптека?", "ru", "hy", ()),
        ("Сегодня у меня хороший день, а завтра я хочу поехать в центр города.", "ru", "hy", ()),
        ("Բարի օր", "hy", "ru", ("добр", "день")),
    ]
    results = []
    ok = True
    for text, source, target, semantic_hints in tests:
        try:
            out = ENGINE.translate(text, source, target)
            low = out.lower()
            semantic_ok = (not semantic_hints) or any(h in low for h in semantic_hints)
            valid = ENGINE._valid_script(out, target) and ENGINE._not_pathological(out) and semantic_ok
            results.append({"source": source, "target": target, "ok": valid, "input": text, "sample": out[:220]})
            ok = ok and valid
        except Exception as exc:
            results.append({"source": source, "target": target, "ok": False, "input": text, "error": str(exc)})
            ok = False
    print("OFFLINE_SELFTEST " + json.dumps({"ok": ok, "results": results}, ensure_ascii=False), flush=True)
    return ok


class Handler(BaseHTTPRequestHandler):
    server_version = "HayerenOffline/1.5"

    def log_message(self, fmt, *args):
        print("HTTP " + (fmt % args), flush=True)

    def _json(self, body, status=200):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/health":
            ready = all((MODELS_ROOT / d / ".ready").exists() for d in MODEL_SPECS)
            return self._json({
                "ok": ready,
                "service": "hayeren-offline-translator",
                "engine": "Helsinki-NLP OPUS-MT + CTranslate2 INT8",
                "version": "1.5",
                "loaded": sorted(ENGINE.engines.keys()),
                "cache": len(ENGINE.cache),
            }, 200 if ready else 503)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/translate":
            return self._json({"error": "not found"}, 404)
        if not SECRET or self.headers.get("x-hayeren-secret", "") != SECRET:
            return self._json({"error": "unauthorized"}, 401)
        try:
            length = min(int(self.headers.get("Content-Length", "0") or 0), 16000)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(body.get("text", "")).strip()
            source = str(body.get("source", "")).strip().lower()
            target = str(body.get("target", "")).strip().lower()
            if not text or len(text) > 4000 or (source, target) not in (("ru", "hy"), ("hy", "ru")):
                return self._json({"error": "invalid request"}, 400)
            started = time.time()
            translated = ENGINE.translate(text, source, target)
            elapsed_ms = round((time.time() - started) * 1000)
            return self._json({
                "translated": translated,
                "provider": "Hayeren Offline · Helsinki-NLP",
                "verified": False,
                "elapsedMs": elapsed_ms,
                "version": "1.5",
            })
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
    try:
        ENGINE.preload()
    except Exception as exc:
        print(f"PRELOAD_ERROR {type(exc).__name__}: {exc}", flush=True)
    threading.Thread(target=selftest, name="hayeren-selftest", daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"HAYEREN_OFFLINE_READY port={PORT} version=1.5", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
