from __future__ import annotations
import json
import os

_FALLBACK_LANG = "en"
_LANG_DIR = os.path.join(os.path.dirname(__file__), "lang")
_CONFIG_PATH = os.path.join(_LANG_DIR, "config.json")

_LANG_FILES: dict[str, str] = {
    "en":    "en",
    "pt-br": "pt-BR",
}

# Cache dos dicts carregados: {codigo_idioma: {chave: texto}}
_LOADED: dict[str, dict[str, str]] = {}

# Idioma ativo para t(). Definido por set_language().
_active_lang: str = _FALLBACK_LANG


def _load_lang(lang_code: str) -> dict[str, str]:

    # Carrega (com cache) o JSON de tradução para lang_code
    if lang_code in _LOADED:
        return _LOADED[lang_code]

    filename = _LANG_FILES.get(lang_code, lang_code)
    path = os.path.join(_LANG_DIR, f"{filename}.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    _LOADED[lang_code] = data
    return data


def set_language(lang_code: str) -> None:

    # Define o idioma ativo
    global _active_lang
    _load_lang(_FALLBACK_LANG)
    _load_lang(lang_code)
    _active_lang = lang_code if lang_code else _FALLBACK_LANG


def t(key: str, *args) -> str:
    active   = _LOADED.get(_active_lang, {})
    fallback = _LOADED.get(_FALLBACK_LANG, {})

    text = active.get(key, fallback.get(key, key))

    if not args:
        return text

    try:
        return text.format(*args)
    except Exception:
        return text


def _load_saved_language() -> str:
    # Lê o idioma salvo em config.json. Retorna "en" em caso de erro.
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        lang = data.get("language", _FALLBACK_LANG)
        return lang if isinstance(lang, str) and lang else _FALLBACK_LANG
    except Exception:
        return _FALLBACK_LANG


def save_language(lang_code: str) -> None:
    # Grava o idioma escolhido em config.json para persistir entre sessões.
    try:
        os.makedirs(_LANG_DIR, exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"language": lang_code}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load_lang(_FALLBACK_LANG)
set_language(_load_saved_language())