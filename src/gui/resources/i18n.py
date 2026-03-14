import copy

from src.gui.resources.translations import TRANSLATIONS


DEFAULT_LANGUAGE = "en"


def load_translations() -> dict:
    return copy.deepcopy(TRANSLATIONS)


def get_translation(translations: dict, language: str, key: str) -> str:
    if language in translations and key in translations[language]:
        return translations[language][key]
    if DEFAULT_LANGUAGE in translations and key in translations[DEFAULT_LANGUAGE]:
        return translations[DEFAULT_LANGUAGE][key]
    return key
