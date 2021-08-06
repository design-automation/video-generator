import os

## Video settings
VIDEO_RES = (1280,720)
HS_VIDEO_RES = (1920,1080)
TITLE_PERIOD = 3 #seconds
FONT = "Ubuntu-Mono"
IDEAL_LENGTH = 12
FONT_SZ = 103

## Audio settings
VOICES = dict(
    en = dict(
            lang_code = ["en-UK", "en-US"], #[0-2] UK
            neural = True,
            ids = ["Amy", "Emma", "Brian", "Joanna", "Kendra", "Kimberly", "Salli", "Joey", "Matthew"]
        ),
    pt = dict(
            lang_code = "pt-BR",
            neural = True,
            ids = ["Camila"]
        ),
    es = dict(
            lang_code = "es-US",
            neural = True,
            ids = ["Lupe"]
        ),
    zh = dict(
            lang_code = "cmn-CN",
            neural = False,
            ids = ["Zhiyu"]
        ),
    fr = dict(
            lang_code = "fr-FR",
            neural = False,
            ids = ["Celine", "Léa", "Mathieu"]
        ),
    de = dict(
            lang_code = "de-DE",
            neural = False,
            ids = ["Marlene", "Vicki", "Hans"]
        ),
    nl = dict(
            lang_code = "nl-NL",
            neural = False,
            ids = ["Lotte", "Ruben"]
        )
)