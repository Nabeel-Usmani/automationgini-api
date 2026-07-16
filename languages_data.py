"""
Bilingual voice demo languages. Each pairs with English using the same
"press 1 for [language] / press 2 for English" router pattern already proven
for Arabic. Voice IDs are real, standard Azure neural voices; several verified
directly against Microsoft's own release notes (Swara/Hindi, Dariya/Russian,
Katja/German).
"""

LANGUAGES = [
    {
        "code": "ar",
        "name": "Arabic",
        "flag": "🇸🇦",
        "press_line": "للغة العربية، اضغط 1 أو قل عربي.",  # "For Arabic, press 1 or say Arabic."
        "azure_voice": "ar-SA-HamedNeural",
        "stt_language": "ar",
    },
    {
        "code": "zh",
        "name": "Chinese (Mandarin)",
        "flag": "🇨🇳",
        "press_line": "中文请按1，或说中文。",  # "For Chinese, press 1, or say Chinese."
        "azure_voice": "zh-CN-XiaoxiaoNeural",
        "stt_language": "zh",
    },
    {
        "code": "hi",
        "name": "Hindi",
        "flag": "🇮🇳",
        "press_line": "हिंदी के लिए 1 दबाएं या हिंदी बोलें।",  # "For Hindi, press 1 or say Hindi."
        "azure_voice": "hi-IN-SwaraNeural",
        "stt_language": "hi",
    },
    {
        "code": "fr",
        "name": "French",
        "flag": "🇫🇷",
        "press_line": "Pour le français, appuyez sur 1 ou dites français.",
        "azure_voice": "fr-FR-DeniseNeural",
        "stt_language": "fr",
    },
    {
        "code": "es",
        "name": "Spanish",
        "flag": "🇪🇸",
        "press_line": "Para español, presione 1 o diga español.",
        "azure_voice": "es-ES-ElviraNeural",
        "stt_language": "es",
    },
    {
        "code": "ru",
        "name": "Russian",
        "flag": "🇷🇺",
        "press_line": "Для русского языка нажмите 1 или скажите русский.",
        "azure_voice": "ru-RU-DariyaNeural",
        "stt_language": "ru",
    },
    {
        "code": "pt",
        "name": "Portuguese",
        "flag": "🇵🇹",
        "press_line": "Para português, pressione 1 ou diga português.",
        "azure_voice": "pt-BR-FranciscaNeural",
        "stt_language": "pt",
    },
    {
        "code": "de",
        "name": "German",
        "flag": "🇩🇪",
        "press_line": "Für Deutsch, drücken Sie 1 oder sagen Sie Deutsch.",
        "azure_voice": "de-DE-KatjaNeural",
        "stt_language": "de",
    },
    {
        "code": "tr",
        "name": "Turkish",
        "flag": "🇹🇷",
        "press_line": "Türkçe için 1'e basın veya Türkçe deyin.",
        "azure_voice": "tr-TR-EmelNeural",
        "stt_language": "tr",
    },
]

LANGUAGE_BY_CODE = {l["code"]: l for l in LANGUAGES}
