import os
import json
import yaml
from __CONSTS__ import LANGUAGES

def _json_to_dict(path):
    json_dict = {}
    with open(path) as json_f:
        json_dict = json.load(json_f)
    return json_dict

def dict_to_json(vid_dict, path):
    with open(path, "w", encoding="utf-8") as json_f:
        json.dump(vid_dict, json_f, ensure_ascii=False, indent=4)

def yaml_to_dict(path):
    ret_dict = {}
    with open(path, "rt") as yaml_f:
        ret_dict = yaml.safe_load(yaml_f)
    return ret_dict

'''
title
display_name
voice
meta
    md
        path
        last_edit
    pre_polly
        path
        last_edit
    srt
        lang
            path
            last_edit
    post
        lang
'''
class VIDEO_OBJ:
    def __init__(self):
        self.__title=""
        self.__display_name=""
        self.__voice=""
        self.__meta=dict(
            md={}, # markdown last edit
            pre_polly={}, # pptx/mp4 last edit
            srt={}
        )
    def as_dict(self):
        return dict(title=self.__title, display_name=self.__display_name, voice=self.__voice, meta=self.__meta)

class COMPONENT:
    def __init__(self, name, _dir, ext):
        self.__path = _dir + "\\" + name + ".%s" % ext
        self.__last_edit = -1
        try:
            self.__last_edit = os.path.getmtime(self.__path)
        except Exception:
            print("%s does not exist" % self.__path)
            self.__last_edit = -1
    def as_dict(self):
        return dict(path=self.__path, last_edit=self.__last_edit)

class Video:
    def __init__(self, path):
        (root,ext) = os.path.splitext(path)
        self.__name = os.path.basename(root)
        self.__ext = ext[1:]
        self.__base_dir = os.path.dirname(path)
        self.__dict = VIDEO_OBJ().as_dict()
        self.__dict["meta"]["md"] = COMPONENT(self.__name, self.__base_dir, "md").as_dict()
        self.__dict["meta"]["pre_polly"] = COMPONENT(self.__name, self.__base_dir, self.__ext).as_dict()
        self.__dict["meta"]["srt"] = {}
        for lang in LANGUAGES:
            lang_append = lang
            if lang == "uk" or lang == "us":
                lang_append = "en"
            srt_name = self.__name + "_%s" % lang_append
            srt_component = COMPONENT(srt_name, self.__base_dir, "srt").as_dict()
            self.__dict["meta"]["srt"][lang_append] = srt_component  
        self.__md_update()
    def __md_update(self):
        md_path = self.get_md_path()
        vid_dict = yaml_to_dict(md_path)
        for key in self.__dict:
            try:
                self.__dict[key] = vid_dict[key]
            except KeyError:
                pass
    def set_md_edit(self, value):
        self.__dict["meta"]["md"]["last_edit"] = value
    def set_pre_polly_edit(self, value):
        self.__dict["meta"]["pre_polly"]["last_edit"] = value
    def set_srt_edit(self, language, value):
        lang = language
        if language == "us" or language == "uk":
            lang = "en"
        self.__dict["meta"]["srt"][lang]["last_edit"] = value
    def get_base_dir(self):
        return self.__base_dir
    def get_file_name(self):
        return self.__name
    def get_ext(self):
        return self.__ext
    def get_md_edit(self):
        return self.__dict["meta"]["md"]["last_edit"]
    def get_md_path(self):
        return self.__dict["meta"]["md"]["path"]  
    def get_pre_polly_edit(self):
        return self.__dict["meta"]["pre_polly"]["last_edit"]
    def get_pre_polly_path(self):
        return self.__dict["meta"]["pre_polly"]["path"]
    def get_srt_edit(self, language):
        lang = language
        if language == "us" or language == "uk":
            lang = "en"
        return self.__dict["meta"]["srt"][lang]["last_edit"]
    def get_srt_path(self, language):
        lang = language
        if language == "us" or language == "uk":
            lang = "en"
        return self.__dict["meta"]["srt"][lang]["path"]
    def get_vid_args(self):
        sh_cpy = dict(self.__dict)
        del sh_cpy["meta"]
        return sh_cpy
    def to_dict(self):
        return self.__dict

class VidsJSON:
    def __init__(self, path, fresh):
        self.__path = path
        self.__dict = self.__to_dict(path, fresh)
    def __to_dict(self, path, fresh):
        vids_dict = None
        if fresh:
            vids_dict = {}
        else:
            vids_dict = _json_to_dict(path)
        return vids_dict
    def set_vid_obj(self, vid_obj):
        self.__dict[vid_obj.get_file_name()] = vid_obj.to_dict()
    def get_md_edit(self, id):
        try:
            return self.__dict[id]["meta"]["md"]["last_edit"]
        except KeyError:
            return -1 
    def get_pre_polly_edit(self, id):
        try:
            return self.__dict[id]["meta"]["pre_polly"]["last_edit"]
        except KeyError:
            return -1
    def get_srt_edit(self, language, id):
        lang=language
        if language == "us" or language == "uk":
            lang = "en"
        try:
            return self.__dict[id]["meta"]["srt"][lang]["last_edit"]
        except KeyError:
            return -1
    def to_JSON(self):
        return dict_to_json(self.__dict, self.__path)