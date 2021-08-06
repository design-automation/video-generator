import os
import json
import subprocess
import re

def _json_to_dict(path):
    json_dict = {}
    with open(path) as json_f:
        json_dict = json.load(json_f)
    return json_dict

def dict_to_json(vid_dict, path):
    with open(path, "w", encoding="utf-8") as json_f:
        json.dump(vid_dict, json_f, ensure_ascii=False, indent=4)
'''
video_file_name
display_name
voice
meta
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
        self.__video_file_name=""
        self.__display_name=""
        self.__voice=""
        self.__meta=dict(
            pre_polly={}, # pptx/mp4 last edit
            srt={}
        )
    def as_dict(self):
        return dict(video_file_name=self.__video_file_name, display_name=self.__display_name, voice=self.__voice, meta=self.__meta)

class COMPONENT:
    def __init__(self, INPUT_PATH, name, _dir, ext):
        if INPUT_PATH[-1] != os.sep:
            INPUT_PATH += os.sep
        self.__full_path = _dir + "\\" + name + ".%s" % ext
        self.__rel_path = self.__full_path.replace(INPUT_PATH, "")
        try:
            # self.__last_git_edit = float(re.search(r"(\d+)", subprocess.run(args=["git", "log" , "-1", "--pretty='format:%ct'", self.__full_path], cwd=os.path.dirname(self.__full_path), capture_output=True, text=True).stdout).group(1))
            self.__last_edit = os.path.getmtime(self.__full_path)
        except Exception as e:
            print("%s NEW FILE" % self.__rel_path)
            self.__last_edit = -1
    def as_dict(self):
        return dict(path=self.__rel_path, last_edit=self.__last_edit)

class Video:
    def __init__(self, INPUT_PATH, path, langs):
        (root,ext) = os.path.splitext(path)
        self.__input_path = INPUT_PATH
        self.__name = os.path.basename(root)
        self.__ext = ext[1:]
        self.__base_dir = os.path.dirname(path)
        self.__dict = VIDEO_OBJ().as_dict()
        self.__dict["meta"]["pre_polly"] = COMPONENT(INPUT_PATH, self.__name, self.__base_dir, self.__ext).as_dict()
        self.__dict["meta"]["srt"] = {}
        for lang in langs:
            srt_name = self.__name + "_%s" % lang
            srt_component = COMPONENT(INPUT_PATH, srt_name, self.__base_dir, "srt").as_dict()
            self.__dict["meta"]["srt"][lang] = srt_component  
    def set_pre_polly_edit(self, value):
        self.__dict["meta"]["pre_polly"]["last_edit"] = value
    def set_vid_args(self, srt_obj):
        script = srt_obj.get_seq("_NA_", 1)["script"]
        arg_dict = json.loads(script)
        for key_name in arg_dict:
            self.__dict[key_name] = arg_dict[key_name]
        self.__dict["video_file_name"] = self.__name
        if self.__dict["voice"] == "":
            self.__dict["voice"] = "0"
        if self.__dict["display_name"] == "":
            raise Exception("Attribute \"display_name\" not found")

    def set_srt_edit(self, language, value):
        self.__dict["meta"]["srt"][language]["last_edit"] = value
    def get_base_dir(self):
        return self.__base_dir
    def get_file_name(self):
        return self.__name
    def get_ext(self):
        return self.__ext
    def get_pre_polly_edit(self):
        return self.__dict["meta"]["pre_polly"]["last_edit"]
    def get_pre_polly_path(self):
        return os.path.join(self.__input_path, self.__dict["meta"]["pre_polly"]["path"])
    def get_srt_edit(self, language):
        return self.__dict["meta"]["srt"][language]["last_edit"]
    def get_srt_path(self, language):
        return os.path.join(self.__input_path, self.__dict["meta"]["srt"][language]["path"])
    def get_vid_args(self):
        sh_cpy = dict(self.__dict)
        del sh_cpy["meta"]
        return sh_cpy
    def to_dict(self):
        return self.__dict

class VidsJSON:
    def __init__(self, INPUT_PATH, path, fresh):
        self.__input_path = INPUT_PATH
        self.__path = path
        self.__last_edit = -1
        self.__dict = self.__to_dict(path, fresh)
    def __to_dict(self, path, fresh):
        vids_dict = None
        if fresh:
            vids_dict = {}
        else:
            vids_dict = _json_to_dict(path)
            try:
                self.__last_edit = float(re.search(r"(\d+)", subprocess.run(args=["git", "log" , "-1", "--pretty='format:%ct'", self.__path], cwd=os.path.dirname(self.__path), capture_output=True, text=True).stdout).group(1))
            except Exception:
                print("%s NEW FILE" % self.__path)
                self.__last_edit = -1
        return vids_dict
    def set_vid_obj(self, vid_obj):
        self.__dict[vid_obj.get_file_name()] = vid_obj.to_dict()
    def get_pre_polly_edit(self, id):
        id = id.replace(self.__input_path, "")
        try:
            return self.__dict[id]["meta"]["pre_polly"]["last_edit"]
        except KeyError:
            return -1
    def get_srt_edit(self, language, id):
        id = id.replace(self.__input_path, "")
        try:
            return self.__dict[id]["meta"]["srt"][language]["last_edit"]
        except KeyError:
            return -1
    def get_last_edit(self):
        return self.__last_edit
    def to_JSON(self):
        return dict_to_json(self.__dict, self.__path)
    def to_dict(self):
        return self.__dict
