'''
video.json = {
        "title" : "YOUTUBE TITLE HERE",
        "description" : "YOUTUBE DESCRIPTION HERE",
        "voice_id" : [int] 1-4 (types of voices available) ** MODULO IF SPECIFIED IS LESS THAN AVAILABLE VOICES
    }

video.json = {
        "title" : "YOUTUBE TITLE HERE",
        "description" : "YOUTUBE DESCRIPTION HERE",
        "voice_id" : [int] 1-4 (types of voices available) ** MODULO IF SPECIFIED IS LESS THAN AVAILABLE VOICES,
        "meta" : {
            video_i: [int] index,
            status: [string] "pre" || "post",
            json_edit: [float] last edit time for JSON (pre_polly), ** Any change should always be reflected on json: descr, or updated uploaded
            pre_polly_id: [string] youtube_video_id
        }
    }

videos.json = {
        "log" : {
            status: [string] "pre" || "post"
            changes: int[] indexes,
            nxt_vid_i: [int] n + 1
        },
        "body" : {
            0 : video_dict (from video.json)
            1 : video_dict
                .
                .
                .
            n : video_dict
        }
    }
'''

import os
import json

class VIDEO_OBJ:
    def __init__(self):
        self.__title=""
        self.__description=""
        self.__voice_id=""
        self.__meta=dict(
            WARNING="DO NOT DELETE meta OR MODIFY ANY meta KEY OTHER THAN pre_polly_id",
            video_i=0,
            status="",
            last_edit=0,
            pre_polly_id="",
            post_polly_id={}
        )
    def as_dict(self):
        return dict(title=self.__title, description=self.__description, voice_id=self.__voice_id, meta=self.__meta)

class VIDEOS_OBJ:
    def __init__(self):
        self.__log=dict(
            status="",
            changes=[],
            nxt_vid_i=0)
        self.__body=dict()
    def as_dict(self):
        return dict(log=self.__log, body=self.__body)

# ALL FUNCTIONS PRESUMES VALID JSON (check logic handled by manager)

def _json_to_dict(path):
    json_dict = {}
    with open(path) as json_f:
        json_dict = json.load(json_f)
    return json_dict

def dict_to_json(vid_dict, path):
    with open(path, "w", encoding="utf-8") as json_f:
        json.dump(vid_dict, json_f, ensure_ascii=False, indent=4)

class VidJSON:
    def __init__(self, path, video_i):
        self.__path = path
        self.__dict = self.__to_dict(path, video_i)
    def __to_dict(self, path, video_i):
        vid_dict = _json_to_dict(path)
        ret_dict = VIDEO_OBJ().as_dict()
        ret_dict["meta"]["video_i"] = video_i
        for key in vid_dict:
            ret_dict[key] = vid_dict[key]
        return ret_dict
    def set_lst_edt(self, value):
        self.__dict["meta"]["last_edit"] = value
    def set_status(self, value):
        self.__dict["meta"]["status"] = value
    def set_pre_id(self, value):
        self.__dict["meta"]["pre_polly_id"] = value
    def set_post_id_dict(self, value):
        self.__dict["meta"]["post_polly_id"] = value
    def get_dict(self):
        return self.__dict
    def get_video_i(self):
        return self.__dict["meta"]["video_i"]
    def get_status(self):
        return self.__dict["meta"]["status"]
    def get_lst_edt(self):
        return self.__dict["meta"]["last_edit"]
    def get_pre_id(self):
        return self.__dict["meta"]["pre_polly_id"]
    def get_post_id_dict(self):
        return self.__dict["meta"]["post_polly_id"]
    def get_vid_args(self):
        sh_cpy = dict(self.__dict)
        del sh_cpy["meta"]
        sh_cpy["tags"] = [self.get_status()]
        return sh_cpy
    def update_JSON(self):
        return dict_to_json(self.__dict,self.__path)

class VidsJSON:
    def __init__(self, path, fresh):
        self.__path = path
        self.__dict = self.__to_dict(path, fresh)
    def __to_dict(self, path, fresh):
        vids_dict = None
        if fresh:
            vids_dict = VIDEOS_OBJ().as_dict()
        else:
            vids_dict = _json_to_dict(path)
        return vids_dict
    def set_status(self, value):
        self.__dict["log"]["status"] = value
    def set_changes(self, value):
        self.__dict["log"]["changes"] = value
    def set_vid_obj(self, vid_obj):
        video_i = str(vid_obj.get_video_i())
        if video_i not in self.__dict["body"]:
            self.__dict["body"][video_i] = vid_obj.get_dict()
            self.__dict["log"]["nxt_vid_i"] = self.__dict["log"]["nxt_vid_i"] + 1
        else:
            self.__dict["body"][video_i] = vid_obj.get_dict()
    def get_nxt_vid_i(self):
        return self.__dict["log"]["nxt_vid_i"]
    def get_changes_lst(self):
        return self.__dict["log"]["changes"]
    def get_body_dict(self):
        return self.__dict["body"]
    def to_JSON(self):
        return dict_to_json(self.__dict, self.__path)