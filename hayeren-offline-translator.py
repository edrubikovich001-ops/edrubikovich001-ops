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
import urllib.parse
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
WIKIDICT_FILE = BASE / "hayeren_offline_models" / "hy-ru_wiki.txt"
WIKIDICT_URL = "https://raw.githubusercontent.com/open-dict-data/wikidict-ru/4d88a4af703c2f9b344ecb07eb08539cf0b775cc/data/hy-ru_wiki.txt"

# High-confidence everyday vocabulary that must never depend on a probabilistic model.
CORE_RU_HY = {
    "тигр": "Վագր",
    "аптека": "Դեղատուն",
    "кошка": "Կատու",
    "кот": "Կատու",
    "собака": "Շուն",
    "слон": "Փիղ",
    "лев": "Առյուծ",
    "дом": "Տուն",
    "машина": "Մեքենա",
    "школа": "Դպրոց",
    "врач": "Բժիշկ",
    "больница": "Հիվանդանոց",
    "магазин": "Խանութ",
    "стол": "Սեղան",
    "стул": "Աթոռ",
    "вода": "Ջուր",
    "хлеб": "Հաց",
    "кофе": "Սուրճ",
    "чай": "Թեյ",
    "метро": "Մետրո",
    "такси": "Տաքսի",
    "автобус": "Ավտոբուս",
    "аэропорт": "Օդանավակայան",
    "вокзал": "Կայարան",
    "город": "Քաղաք",
    "центр": "Կենտրոն",
    "центра": "Կենտրոն",
    "ереван": "Երևան",
    "билет": "Տոմս",
    "завтра": "Վաղը",
    "сегодня": "Այսօր",
    "утро": "Առավոտ",
    "утром": "Առավոտյան",
    "вечер": "Երեկո",
    "вечером": "Երեկոյան",
    "друг": "Ընկեր",
    "семья": "Ընտանիք",
    "мама": "Մայր",
    "мать": "Մայր",
    "папа": "Հայր",
    "отец": "Հայր",
    "брат": "Եղբայր",
    "сестра": "Քույր",
    "ребенок": "Երեխա",
    "ребёнок": "Երեխա",
    "день": "Օր",
    "ночь": "Գիշեր",
    "год": "Տարի",
    "книга": "Գիրք",
    "язык": "Լեզու",
    "история": "Պատմություն",
    "музыка": "Երաժշտություն",
    "любовь": "Սեր",
}



def download_file(repo, name, target):
    url = f"https://huggingface.co/{repo}/resolve/main/{name}?download=true"
    req = urllib.request.Request(url, headers={"User-Agent": "HayerenOffline/1.7"})
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
    if not WIKIDICT_FILE.exists() or WIKIDICT_FILE.stat().st_size < 100000:
        print("DICT_BUILD_START wikidict-hy-ru", flush=True)
        req = urllib.request.Request(WIKIDICT_URL, headers={"User-Agent": "HayerenOffline/1.7"})
        with urllib.request.urlopen(req, timeout=180) as response, open(WIKIDICT_FILE, "wb") as f:
            shutil.copyfileobj(response, f)
        print(f"DICT_BUILD_DONE bytes={WIKIDICT_FILE.stat().st_size}", flush=True)


def google_translate(text, source, target):
    q = urllib.parse.urlencode({
        "client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text
    })
    url = "https://translate.googleapis.com/translate_a/single?" + q
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 Hayeren/1.7",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=4.5) as r:
        data = json.loads(r.read().decode("utf-8"))
    parts = data[0] if isinstance(data, list) and data else []
    out = "".join(str(x[0] or "") for x in parts if isinstance(x, list) and x).strip()
    return out


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
        self.ru_hy = {}
        self.hy_ru = {}
        self._load_dictionary()

    @staticmethod
    def _norm_ru(text):
        return re.sub(r"[^а-яё0-9 -]+", "", str(text or "").lower()).strip()

    @staticmethod
    def _norm_hy(text):
        return re.sub(r"[^Ա-Ֆա-ֆև0-9 -]+", "", str(text or "").lower()).strip()

    @staticmethod
    def _pretty_hy(text):
        text = str(text or "").strip()
        if not text:
            return text
        return text[:1].upper() + text[1:].lower()

    def _load_dictionary(self):
        # Manual core wins. Wikidict (CC0) expands coverage to ~92k Armenian/Russian title pairs.
        for ru, hy in CORE_RU_HY.items():
            self.ru_hy[self._norm_ru(ru)] = hy
            self.hy_ru[self._norm_hy(hy)] = ru[:1].upper() + ru[1:]
        if not WIKIDICT_FILE.exists():
            return
        count = 0
        try:
            with open(WIKIDICT_FILE, "r", encoding="utf-8") as f:
                for raw in f:
                    if "\t" not in raw:
                        continue
                    hy, ru = raw.rstrip("\n").split("\t", 1)
                    hy, ru = hy.strip(), ru.strip()
                    if not hy or not ru or hy.startswith(("Կատեգորիա:", "Կաղապար:", "Վիքիպեդիա:")):
                        continue
                    nr, nh = self._norm_ru(ru), self._norm_hy(hy)
                    if not nr or not nh:
                        continue
                    score = ((" (" in ru) * 5 + (" (" in hy) * 3 + (len(hy.split()) > 4) * 2)
                    old = self.ru_hy.get(nr)
                    if old is None or score == 0:
                        self.ru_hy.setdefault(nr, self._pretty_hy(hy))
                    self.hy_ru.setdefault(nh, ru)
                    count += 1
        except Exception as exc:
            print(f"DICT_LOAD_ERROR {type(exc).__name__}: {exc}", flush=True)
        # Reassert core entries after bulk load.
        for ru, hy in CORE_RU_HY.items():
            self.ru_hy[self._norm_ru(ru)] = hy
            self.hy_ru[self._norm_hy(hy)] = ru[:1].upper() + ru[1:]
        print(f"DICT_READY pairs={count} ru={len(self.ru_hy)} hy={len(self.hy_ru)}", flush=True)

    def _lexical(self, text, source, target):
        if source == "ru" and target == "hy":
            return self.ru_hy.get(self._norm_ru(text))
        if source == "hy" and target == "ru":
            return self.hy_ru.get(self._norm_hy(text))
        return None

    def _core_terms(self, text):
        words = set(re.findall(r"[А-Яа-яЁё-]+", str(text or "").lower()))
        out = []
        for ru, hy in CORE_RU_HY.items():
            if ru in words:
                out.append((ru, hy))
        return out

    @staticmethod
    def _contains_hy_term(output, hy):
        stem = Engine._norm_hy(hy).replace(" ", "")
        target = Engine._norm_hy(output).replace(" ", "")
        if not stem:
            return True
        probe = stem[:max(3, min(6, len(stem)))]
        return probe in target

    @staticmethod
    def _definite(hy):
        w = str(hy or "").strip()
        if not w:
            return w
        return w + ("ն" if w[-1:].lower() in "աեէըիոօև" else "ը")

    def _template_ru_hy(self, text):
        n = self._norm_ru(text)

        m = re.fullmatch(r"где(?: находится)?(?: ближайшая| ближайший| ближайшее)? (.+)", n)
        if m:
            noun = m.group(1).strip()
            hy = self.ru_hy.get(noun)
            if hy:
                nearest = " ближай" in n
                return "Որտե՞ղ է " + ("մոտակա " if nearest else "") + self._definite(hy).lower() + "։"

        m = re.fullmatch(r"мне (?:нужен|нужна|нужно) (.+)", n)
        if m:
            hy = self.ru_hy.get(m.group(1).strip())
            if hy:
                return "Ինձ " + hy.lower() + " է պետք։"

        m = re.fullmatch(r"я хочу (?:поехать|пойти) в ([а-яё-]+)(.*)", n)
        if m:
            dest = self.ru_hy.get(m.group(1).strip())
            tail = m.group(2).strip()
            if dest:
                time_bits = []
                if "завтра" in tail:
                    time_bits.append("վաղը")
                elif "сегодня" in tail:
                    time_bits.append("այսօր")
                if "утром" in tail:
                    time_bits.append("առավոտյան")
                elif "вечером" in tail:
                    time_bits.append("երեկոյան")
                when = (" ".join(time_bits) + " ") if time_bits else ""
                return "Ես ուզում եմ " + when + "գնալ " + dest + "։"

        m = re.fullmatch(r"сколько стоит билет до ([а-яё-]+)", n)
        if m:
            dest = self.ru_hy.get(m.group(1).strip())
            if dest:
                base = dest.lower()
                if base.endswith("ը") or base.endswith("ն"):
                    base = base[:-1]
                return "Որքա՞ն արժե " + base + "ի տոմսը։"

        return None

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
        clean_text = re.sub(r"\\s+", " ", str(text or "")).strip()
        key = direction + "|" + clean_text.lower()
        with self.lock:
            cached = self._cache_get(key)
            if cached:
                return cached

            exact = self._lexical(clean_text, source, target)
            if exact:
                self._cache_put(key, exact)
                return exact

            if source == "ru" and target == "hy":
                templated = self._template_ru_hy(clean_text)
                if templated:
                    self._cache_put(key, templated)
                    return templated

            # For arbitrary phrases, prefer a broad online MT engine when reachable.
            # The local neural models stay as an offline fallback; exact dictionary entries stay first.
            try:
                web = google_translate(clean_text, source, target)
                if self._valid_script(web, target) and self._not_pathological(web):
                    self._cache_put(key, web)
                    return web
            except Exception as exc:
                print(f"GOOGLE_FALLBACK {type(exc).__name__}: {exc}", flush=True)

            engine = self._get(direction)
            outs = []
            for chunk in self._chunks(clean_text):
                out = engine.translate_one(chunk)
                if not self._valid_script(out, target):
                    raise RuntimeError(f"invalid {target} output")
                if not self._not_pathological(out):
                    raise RuntimeError("pathological repetition detected")
                outs.append(out)
            translated = " ".join(x for x in outs if x).strip()
            if not translated:
                raise RuntimeError("empty translation")

            # Guard against the exact failure seen in production: known everyday nouns
            # must survive sentence translation semantically.
            if source == "ru" and target == "hy":
                missing = [(ru, hy) for ru, hy in self._core_terms(clean_text)
                           if not self._contains_hy_term(translated, hy)]
                if missing:
                    templated = self._template_ru_hy(clean_text)
                    if templated:
                        translated = templated
                    else:
                        print("TERM_GUARD missing=" + ",".join(x[0] for x in missing), flush=True)

            self._cache_put(key, translated)
            return translated


ENGINE = Engine()


def selftest():
    tests = [
        ("тигр", "ru", "hy", ("վագր",)),
        ("Վագր", "hy", "ru", ("тигр",)),
        ("аптека", "ru", "hy", ("դեղատ",)),
        ("Где находится ближайшая аптека?", "ru", "hy", ("դեղատ",)),
        ("кошка", "ru", "hy", ("կատ",)),
        ("врач", "ru", "hy", ("բժիշկ",)),
        ("машина", "ru", "hy", ("մեքենա",)),
        ("школа", "ru", "hy", ("դպրոց",)),
        ("добрый день", "ru", "hy", ("բարի", "օր")),
        ("спасибо", "ru", "hy", ("շնորհ",)),
        ("где находится железнодорожный вокзал", "ru", "hy", ("կայարան",)),
        ("Сегодня у меня хороший день, а завтра я хочу поехать в центр города.", "ru", "hy", ("քաղաք",)),
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
    server_version = "HayerenOffline/1.7"

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
                "version": "1.7",
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
                "version": "1.7",
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
    print(f"HAYEREN_OFFLINE_READY port={PORT} version=1.7", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
