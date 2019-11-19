COURSE_PATH = "input\\Course\\"
LANGUAGES = ["uk", "zh"] # available: ["us", "uk", "zh", "pt", "es"]
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
        )
)