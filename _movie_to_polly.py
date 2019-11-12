import re
import os
import sys
import glob
import math
import datetime
import time
import shutil

from moviepy.editor import *
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from _get_by_type import *

IMAGEMAGICK_BINARY = os.getenv('IMAGEMAGICK_BINARY', 'C:\\Program Files\\ImageMagick-7.0.8-Q16\\magick.exe')
OUTPUT_FDR = "output"
# example folder structure:
# |_VIDEOS
#   |_TOPIC1
#     |_output_en
#       | # en polly mp3s
#     |_output_cn
#       | # cn polly mp3s
#     |_output_VIDEOS
#       | # cut mp4
#     | *.json
#     | *.mp4
#     | *.srt
#     | *_comp_en.mp4
#     | *_comp_cn.mp4

TITLE_PERIOD = 3 #seconds
PAUSE_PERIOD = 0.7 #seconds
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

class ToPollyMP4:
    def __init__(self, folder):
        self.__path = get_paths_by_typ(folder, "mp4")[0]
        self.__name = re.search(r"\\[\d+]\\(.*).mp4",self.__path).group(1)
        self.__folder = folder
    def get_folder(self):
        return self.__folder
    def get_path(self): # gets path to MP4 in folder
        return self.__path
    def get_name(self):
        return self.__name

class ToPollySRT:
    def __init__(self, folder, languages):
        self.__voices = {lang: VOICES[lang] for lang in languages}
        self.__path = get_paths_by_typ(folder, "srt")[0]
        self.__name = re.search(r"\\[\d+]\\(.*).srt",self.__path).group(1)
        self.__seq_dict = self.__seq_dict(self.__path)
        self.__folder = folder
        self.__n_seq

    def get_full_dict(self): #for errors
        return self.__seq_dict
    def get_name(self):
        return self.__name
    def get_path(self):
        return self.__path
    def get_seq(self, language, n):
        lang = language
        if lang == "CUT":
            lang = list(self.__voices.keys())[0]
        return self.__seq_dict[lang][n]
    def get_n_seq(self):
        return self.__n_seq
    def get_folder(self):
        return self.__folder
    def get_languages(self):
        return self.__voices
    def set_seq_end(self, language, seq_n, seconds):
        start_secs = _to_seconds(self.__seq_dict[language][seq_n]["script_start"])
        end_secs = start_secs + seconds
        self.__seq_dict[language][seq_n]["script_end"] = _to_time_str(end_secs)
    def update_script(self, language, seq_n, script):
        self.__seq_dict[language][seq_n]["script"] = script
    def update_SRT(self, language): 
        self.__rebuild_dict(language)
        tar_path = self.__folder + "..\\..\\POST_SRT\\" + self.__name + language + ".srt"
        with open(tar_path, "wt", encoding="utf-8") as srt_f:
            for seq_n in self.__seq_dict[language]:
                if seq_n != 1:
                    self.__update_seq_start(language, seq_n)
                srt_f.write(self.__seq_for_SRT(language, seq_n))
        print("\nUpdated SRT (%s) created at %s" % (self.__path, tar_path))
    def __seq_dict(self,srt_file): # cut SRT into timestamp dict
        seq_dict = {lang:{} for lang in self.__voices}
        contents = []
        seq_n = 1
        with open(srt_file, "rt") as f:
            for line in f:
                contents.append(line)
            for line_i in range(0,len(contents)):
                if contents[line_i]==(str(seq_n)+"\n"):
                    matches = re.findall(r"(\d\d:\d\d:\d\d,\d\d\d)",contents[line_i + 1])
                    script_i = 2
                    script = ""
                    while contents[line_i + script_i] != "\n":
                        script += contents[line_i + script_i][:-1] + " "
                        script_i += 1
                    for lang in self.__voices:
                        seq_dict[lang][seq_n] = {"script_start": matches[0],
                                        "script_end": "",
                                        "script": script}
                    seq_n += 1
            self.__n_seq = seq_n - 1 #-1
        return seq_dict

    def __rebuild_dict(self, language):
        new_dict = {}
        n_seq_i = 1

        BASE_START = _to_seconds(self.__seq_dict[language][1]["script_start"])
        for seq_i in self.__seq_dict[language]:
            seq_script = self.__seq_dict[language][seq_i]["script"]
            ori_len = len(seq_script)
            print("script start: " + self.__seq_dict[language][seq_i]["script_start"])
            print("script end: " + self.__seq_dict[language][seq_i]["script_end"])
            ori_start = _to_seconds(self.__seq_dict[language][seq_i]["script_start"]) + TITLE_PERIOD - BASE_START
            ori_end = _to_seconds(self.__seq_dict[language][seq_i]["script_end"]) + TITLE_PERIOD - BASE_START
            ori_period = ori_end - ori_start
            script_splt = _split_script(seq_script)
            n_script_splt = len(script_splt)
            ori_period -= (n_script_splt - 1) * PAUSE_PERIOD
            prev_end = ori_start
            for script in script_splt:
                splt_len = len(script)
                splt_period = splt_len/ori_len * ori_period
                new_start = prev_end
                new_end = new_start + splt_period + PAUSE_PERIOD
                seq_dict = dict(
                    script=script,
                    script_start=_to_time_str(new_start),
                    script_end=_to_time_str(new_end)
                )
                new_dict[n_seq_i] = seq_dict
                prev_end = new_end
                n_seq_i += 1
        # self.__n_seq = n_seq_i - 1
        self.__seq_dict[language] = new_dict          
    
    def __seq_for_SRT(self, language, seq_n):
        time_stamp = "%s --> %s"% (self.__seq_dict[language][seq_n]["script_start"], self.__seq_dict[language][seq_n]["script_end"])
        return "%s\n%s\n%s\n\n" % (str(seq_n), time_stamp, self.__seq_dict[language][seq_n]["script"])
    
    def __update_seq_start(self, language, seq_n):
        prev_end = _to_seconds(self.__seq_dict[language][seq_n-1]["script_end"])
        curr_start = _to_seconds(self.__seq_dict[language][seq_n]["script_start"])
        if prev_end > curr_start:
            self.__seq_dict[language][seq_n]["script_start"] = _to_time_str(float(prev_end))

def _split_script(script):
    ret_script = re.sub(r"([^\w\s])","\\1#",script)
    ret_script = ret_script.split("#")
    return ret_script

def _to_seconds(time_str):
    ms = float(('.' + time_str.split(',')[1]).zfill(3))
    x = time.strptime(time_str.split(',')[0],'%H:%M:%S')
    return datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() + ms

def _to_time_str(f_seconds):
    time_str = str(datetime.timedelta(seconds = f_seconds))
    matches = re.search(r"(\d+):(\d+\:\d+)\.*(\d*)", time_str)
    matches_3 = matches.group(3).zfill(3)[:3]
    return "%s:%s,%s" % (matches.group(1).zfill(2), matches.group(2), matches_3)

def _translate(session, str_to_translate, tar_lang):
    translate = session.client("translate")
    try:
        result = translate.translate_text(Text=str_to_translate, SourceLanguageCode="en", TargetLanguageCode=tar_lang)
    except (BotoCoreError, ClientError) as error:
        print(error)
        sys.exit(-1)
    return result.get('TranslatedText')

def _polly(session, output_fdr, file_name, script, voice_id, neural):
    polly = session.client("polly")
    str_frnt = "<speak>"
    str_back = "</speak>"
    text = str_frnt + script + str_back
    engine = "standard"
    if neural:
        engine = "neural"
    try:
        response = polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId=voice_id, Engine=engine, TextType="ssml")
    except (BotoCoreError, ClientError) as error:
        print(error)
        sys.exit(-1)

    if "AudioStream" in response:
        with closing(response["AudioStream"]) as stream:
            output = os.path.join(output_fdr, file_name)
            try:
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                print(error)
                sys.exit(-1)
    else:
        print("Could not stream audio")
        sys.exit(-1)

def _file_idx(file_name):
    return re.search(r"_(\d\d\d)\.",file_name).group(1)

def cut_MP4(mp4_obj, srt_obj): # returns mp4s in subfolder
    clip = VideoFileClip(mp4_obj.get_path())
    output_fdr = mp4_obj.get_folder() + OUTPUT_FDR + "_VIDEOS\\"
    os.makedirs(output_fdr, exist_ok=True)
    num_seq = srt_obj.get_n_seq()
    for seq_i in range(1, num_seq + 1):#range(0, num_seq)
        script_start = srt_obj.get_seq("CUT", seq_i)["script_start"]
        new_clip = None
        if seq_i == num_seq:#num_seq-1
            new_clip = clip.subclip(script_start)
        else:
            next_start = srt_obj.get_seq("CUT", seq_i + 1)["script_start"]
            new_clip = clip.subclip(script_start, next_start)
        
        prev_end = script_start
        file_name = mp4_obj.get_name() + "_" + str(seq_i).zfill(3) + ".mp4"
        output_path = output_fdr + file_name
        new_clip.write_videofile(output_path, audio=False)

def to_Polly(srt_obj, language, voice_id, neural):# returns mp3s in subfolder
    session = Session()
    output_fdr = srt_obj.get_folder() + OUTPUT_FDR + "_%s\\" % language
    os.makedirs(output_fdr, exist_ok=True)
    for seq_i in range(1, srt_obj.get_n_seq()+1): #range(0, srt_obj.get_n_seq())
        script = srt_obj.get_seq(language, seq_i)["script"]
        if language!="uk" and language!="us":
            script = _translate(session, script, language)
            srt_obj.update_script(language, seq_i, script)

        file_name = srt_obj.get_name() + "_" + str(seq_i).zfill(3) + ".mp3"
        output_path = output_fdr + file_name
        print("\nCommunicating to AWS Polly")
        _polly(session=session, output_fdr=output_fdr, file_name=file_name, script=script, voice_id=voice_id , neural=neural)
        aud_out = glob.glob(output_fdr + "*.mp3")[seq_i-1]
        print("Polly MP3 saved at %s" % (aud_out))
        polly_aud = AudioFileClip(aud_out)
        srt_obj.set_seq_end(language, seq_i, polly_aud.duration)
        polly_aud.reader.close_proc()
    srt_obj.update_SRT(language)

def composite_MP4(language, folder, vid_name, title):
    video_res = (1080,720)
    fade_color = [255,255,255]
    vid_clips = sorted(glob.glob(folder + OUTPUT_FDR + "_VIDEOS\\" + "*.mp4"), key=_file_idx)

    aud_clips = sorted(glob.glob(folder + OUTPUT_FDR + "_%s\\" % language + "*.mp3"), key=_file_idx)
    if language!="uk" and language!="us":
        title += "\n(%s)" % language
    title_clip = TextClip(txt=title, size=video_res, method="label", font="Ubuntu-Mono", color="black", bg_color="white", fontsize=103).set_duration("00:00:0%s" % (TITLE_PERIOD)).fadeout(duration=1, final_color=fade_color)
    vid_list = [title_clip]
    for i in range(0,len(vid_clips)):
        vid_clip = VideoFileClip(vid_clips[i])
        aud_clip = AudioFileClip(aud_clips[i])
        if (vid_clip.duration < aud_clip.duration):
            vid_clip = vid_clip.set_duration(aud_clip.duration)
        if i==0:
            vid_list.append(vid_clip.set_audio(aud_clip).fadein(duration=1, initial_color=fade_color))
        else:
            vid_list.append(vid_clip.set_audio(aud_clip))

    composite = concatenate_videoclips(vid_list).resize(height=720)
    composite.fps = 30
    composite_path = folder + vid_name + "_%s_comp.mp4" % language
    composite.write_videofile(composite_path)

    print("Job Complete")
    return composite_path
