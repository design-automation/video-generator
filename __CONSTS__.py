import os

## Course Settings
EDX_COURSE = 'procedural_modelling'
COURSE_PATH = ""

#S3
S3_bucket = "mooc-s3cf"
S3_folder = "videos"

## Video settings
VIDEO_RES = (1080,720)
TITLE_PERIOD = 3 #seconds
FONT = "Ubuntu-Mono"
IDEAL_LENGTH = 12
FONT_SZ = 103

## Audio settings
LANGUAGES = ["uk", "zh"] # available: refer to keys of VOICES below
VOICES = dict(
    us = dict(
            lang_code = "en-US", # usable for translate api
            neural = True,
            ids = ["Joanna", "Kendra", "Kimberly", "Salli", "Joey", "Matthew"]
        ),
    uk = dict(
            lang_code = "en-GB",
            neural = True,
            ids = ["Amy", "Emma", "Brian"]
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