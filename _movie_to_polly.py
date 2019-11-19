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
from __CONSTS__ import VOICES, VIDEO_RES, TITLE_PERIOD, IMAGEMAGICK_BINARY

OUTPUT_FDR = "output"
PAUSE_PERIOD = 0.7 #seconds

class ToPollyMP4:
    def __init__(self, mp4_path):
        self.__path = mp4_path
        (root,ext) = os.path.splitext(mp4_path)
        self.__name = os.path.basename(root)
        self.__folder = os.path.dirname(mp4_path)
    def get_folder(self):
        return self.__folder
    def get_path(self): # gets path to MP4 in folder
        return self.__path
    def get_name(self):
        return self.__name

class ToPollySRT:
    def __init__(self, srt_path, language):
        self.__language = language
        self.__voices = {language: VOICES[language]}
        self.__path = srt_path
        (root,ext) = os.path.splitext(srt_path)
        self.__name = os.path.basename(root)
        self.__seq_dict = self.__seq_dict(self.__path)
        self.__folder = os.path.dirname(srt_path)
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
            lang = self.__language
        return self.__seq_dict[lang][n]
    def get_n_seq(self):
        return self.__n_seq
    def get_folder(self):
        return self.__folder
    def get_voices(self):
        return self.__voices
    def get_language(self):
        return self.__language
    def set_seq_end(self, seq_n, seconds):
        language = self.__language
        start_secs = _to_seconds(self.__seq_dict[language][seq_n]["script_start"])
        end_secs = start_secs + seconds
        self.__seq_dict[language][seq_n]["script_end"] = _to_time_str(end_secs)
    def update_script(self, seq_n, script):
        language = self.__language
        self.__seq_dict[language][seq_n]["script"] = script
    def update_SRT(self): 
        language = self.__language
        lang_append = language
        if lang_append == "uk" or lang_append == "us":
            lang_append = "en"
        else:
            self.__write_base_lang(lang_append)
        self.__rebuild_dict()    
        tar_path = self.__folder + "\\"+ self.__name[:-3] + "_sub_" + lang_append + ".srt"
        
        with open(tar_path, "wt", encoding="utf-8") as srt_f:
            for seq_n in self.__seq_dict[language]:
                if seq_n != 1:
                    self.__update_seq_start(seq_n)
                srt_f.write(self.__seq_for_SRT(seq_n))
        print("\nUpdated SRT (%s) created at %s" % (self.__path, tar_path))
    def __write_base_lang(self, language):
        with open(self.__folder + "\\"+ self.__name[:-3] + "_" + language + ".srt", "wt", encoding="utf-8") as srt_f:
            for seq_n in self.__seq_dict[language]:
                if seq_n != 1:
                    self.__update_seq_start(seq_n)
                srt_f.write(self.__seq_for_SRT(seq_n))
    def __seq_dict(self,srt_file): # cut SRT into timestamp dict
        seq_dict = {lang:{} for lang in self.__voices}
        contents = []
        seq_n = 1
        with open(srt_file, "rt", encoding="utf-8") as f:
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

    def __rebuild_dict(self):
        language = self.__language
        new_dict = {}
        n_seq_i = 1

        BASE_START = _to_seconds(self.__seq_dict[language][1]["script_start"])
        for seq_i in self.__seq_dict[language]:
            seq_script = self.__seq_dict[language][seq_i]["script"]
            ori_len = len(seq_script)
            if seq_script == "":
                continue
            ori_start = _to_seconds(self.__seq_dict[language][seq_i]["script_start"]) + TITLE_PERIOD - BASE_START
            ori_end = _to_seconds(self.__seq_dict[language][seq_i]["script_end"]) + TITLE_PERIOD - BASE_START
            ori_period = ori_end - ori_start
            script_splt = _split_script(seq_script, language)
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
    
    def __seq_for_SRT(self, seq_n):
        language = self.__language
        time_stamp = "%s --> %s"% (self.__seq_dict[language][seq_n]["script_start"], self.__seq_dict[language][seq_n]["script_end"])
        return "%s\n%s\n%s\n\n" % (str(seq_n), time_stamp, self.__seq_dict[language][seq_n]["script"])
    
    def __update_seq_start(self, seq_n):
        language = self.__language
        prev_end = _to_seconds(self.__seq_dict[language][seq_n-1]["script_end"])
        curr_start = _to_seconds(self.__seq_dict[language][seq_n]["script_start"])
        if prev_end > curr_start:
            self.__seq_dict[language][seq_n]["script_start"] = _to_time_str(float(prev_end))

def _split_script(script, language): # to create separate split functions for different languages !!!!!!!!!!!!!!!!!!!!!!!!!!!!
    if language == "uk" or language == "us":
        return _split_script_en(script)
    elif language == "zh":
        return _split_script_zh(script)
    else:
        raise Exception("Language SRT not implemented")

def _split_script_zh(script):
    ret_script = re.sub(r"([^\w\s])","\\1#",script)
    ret_script = ret_script.split("#")
    return ret_script

def _split_script_en(script): 
    ret_script = re.sub("([\\.\\,\\?\\;\\!])\s","\\1#",script)
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
    return re.search(r"-(\d+)\.",file_name).group(1)

def cut_MP4(mp4_obj, srt_obj): # returns mp4s in subfolder
    clip = VideoFileClip(mp4_obj.get_path())
    output_fdr = mp4_obj.get_folder() + "\\" + mp4_obj.get_name() +"\\" + OUTPUT_FDR + "_VIDEOS\\"
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
        file_name = mp4_obj.get_name() + "-" + str(seq_i).zfill(3) + ".mp4"
        output_path = output_fdr + file_name
        new_clip.write_videofile(output_path, audio=False)

def to_Polly(srt_obj, voice_id, neural):# returns mp3s in subfolder
    session = Session()
    language = srt_obj.get_language()
    output_fdr = srt_obj.get_folder() + "\\" + srt_obj.get_name()[:-3] +"\\" + OUTPUT_FDR + "_%s\\" % language
    os.makedirs(output_fdr, exist_ok=True)
    aud_i = 0
    for seq_i in range(1, srt_obj.get_n_seq()+1): #range(0, srt_obj.get_n_seq())
        script = srt_obj.get_seq(language, seq_i)["script"]
        if script!="":
            if srt_obj.get_name()[-2:] == "en" and (language!="uk" and language!="us"): # translate
                script = _translate(session, script, language)
                srt_obj.update_script(seq_i, script)
            file_name = srt_obj.get_name() + "-" + str(seq_i).zfill(3) + ".mp3"
            output_path = output_fdr + file_name
            print("\nCommunicating to AWS Polly")
            _polly(session=session, output_fdr=output_fdr, file_name=file_name, script=script, voice_id=voice_id , neural=neural)
            aud_out = glob.glob(output_fdr + "*.mp3")[aud_i]
            aud_i += 1
            print("Polly MP3 saved at %s" % (aud_out))
            polly_aud = AudioFileClip(aud_out)
            srt_obj.set_seq_end(seq_i, polly_aud.duration)
            polly_aud.reader.close_proc()
        else:
            srt_obj.set_seq_end(seq_i, PAUSE_PERIOD)
    srt_obj.update_SRT()

def composite_MP4(language, folder, vid_name, title):
    return _composite_video("MP4", language, folder, vid_name, title)

def composite_PNGs(language, folder, vid_name, title):    
    return _composite_video("PPTX", language, folder, vid_name, title)

def _composite_video(typ, language, folder, vid_name, title):
    fade_color = [255,255,255]
    aud_clips = sorted(glob.glob(folder + "\\" + OUTPUT_FDR + "_%s\\" % language + "*.mp3"), key=_file_idx)
    aud_dict = {int(_file_idx(aud_clips[i])):aud_clips[i] for i in range(0, len(aud_clips))}

    if language!="uk" and language!="us":
        title += "\n(%s)" % language
    title_clip = TextClip(txt=title, size=VIDEO_RES, method="label", font="Ubuntu-Mono", color="black", bg_color="white", fontsize=103).set_duration("00:00:0%s" % (TITLE_PERIOD)).fadeout(duration=1, final_color=fade_color)
    vid_list = [title_clip]

    if typ == "MP4":
        vid_clips = sorted(glob.glob(folder + "\\" + OUTPUT_FDR + "_VIDEOS\\" + "*.mp4"), key=_file_idx)
        for i in range(0,len(vid_clips)):
            vid_clip = VideoFileClip(vid_clips[i])
            vid_idx = int(_file_idx(vid_clips[i]))
            aud_clip = AudioFileClip(aud_dict[vid_idx])
            if (vid_clip.duration < aud_clip.duration):
                vid_clip = vid_clip.set_duration(aud_clip.duration)
            if i==0:
                vid_list.append(vid_clip.set_audio(aud_clip).fadein(duration=1, initial_color=fade_color))
            else:
                vid_list.append(vid_clip.set_audio(aud_clip))
    else:
        slide_pngs = sorted(glob.glob(folder + "\\images\\" + "*.png"), key=_file_idx)
        for i in range(0,len(slide_pngs)):
            slide_clip = ImageClip(slide_pngs[i])
            slides_idx = int(_file_idx(slide_pngs[i])) + 1
            try:
                aud_clip = AudioFileClip(aud_dict[slides_idx])
                buffer = 0
                if aud_clip.duration > 5:
                    buffer = PAUSE_PERIOD
                slide_clip = slide_clip.set_duration(aud_clip.duration + buffer).set_audio(aud_clip)
            except KeyError:
                slide_clip = slide_clip.set_duration(PAUSE_PERIOD)
                pass
            if i==0:
                vid_list.append(slide_clip.fadein(duration=1, initial_color=fade_color))
            else:
                vid_list.append(slide_clip)

    composite = concatenate_videoclips(vid_list).resize(height=720)
    composite.fps = 30
    composite_path = folder + "\\" + vid_name + "_%s_comp.mp4" % language
    composite.write_videofile(composite_path)

    print("Job Complete")
    return composite_path