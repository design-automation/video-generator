import re
import os
import sys
import glob
import math
import datetime
import time
import shutil
import json
import logging

from moviepy.editor import *
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing

from vid_gen.__CONSTS__ import VOICES, HS_VIDEO_RES, VIDEO_RES, TITLE_PERIOD, FONT, FONT_SZ, IDEAL_LENGTH
from vid_gen import _xml_friendly
from vid_gen._get_by_type import *
from aws_cred import __AWS__




OUTPUT_FDR = "output"
PAUSE_PERIOD = 1 #seconds
logging.basicConfig(filename='errors.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

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
        self.__en_path = "%s_%s%s" % (root[:-3], "en", ext)
        self.__seq_dict = self.__create_seq_dict(self.__path)
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
        if lang == "_NA_":
            lang = self.__language
        return self.__seq_dict[lang][n]
    def get_seq_duration(self, language, n):
        lang = language
        if lang == "_NA_":
            lang = self.__language
        start_seconds = _to_seconds(self.__seq_dict[lang][n]["script_start"])
        end_seconds = _to_seconds(self.__seq_dict[lang][n]["script_end"])
        return end_seconds - start_seconds
    def get_n_seq(self):
        return self.__n_seq
    def get_folder(self):
        return self.__folder
    def get_voices(self):
        return self.__voices
    def get_language(self):
        return self.__language
    def push_seq(self, seq_n, period):
        language = self.__language
        for i in range(seq_n, self.get_n_seq() + 1):
            try:
                next_start = _to_seconds(self.__seq_dict[language][i + 1]["script_start"])
                next_end = _to_seconds(self.__seq_dict[language][i + 1]["script_end"])
                self.__seq_dict[language][i + 1]["script_start"] = _to_time_str(next_start + period)
                self.__seq_dict[language][i + 1]["script_end"] = _to_time_str(next_end + period)
            except KeyError:
                pass
    def set_seq_start(self, seq_n, seconds):
        language = self.__language
        self.__seq_dict[language][seq_n]["script_start"] = _to_time_str(seconds)
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
        if language != "en":
            self.__write_base_lang(language)
        new_dict = self.__rebuild_dict()    
        tar_path = self.__folder + "\\"+ self.__name[:-3] + "_sub_" + language + ".srt"
        
        with open(tar_path, "wb") as srt_f:
            for seq_n in new_dict:
                srt_f.write(self.__seq_for_SRT(seq_n, new_dict).encode("ascii", "ignore"))
        print("\nUpdated SRT (%s) created at %s" % (self.__path, tar_path))
    def __write_base_lang(self, language):
        with open(self.__folder + "\\"+ self.__name[:-3] + "_" + language + ".srt", "wt", encoding="utf-8") as srt_f:
            for seq_n in self.__seq_dict[language]:
                srt_f.write(self.__seq_for_SRT(seq_n))
    def __create_seq_dict(self,srt_file): # cut SRT into timestamp dict
        seq_dict = {lang:{} for lang in self.__voices}
        contents = []
        seq_n = 1
        with open(srt_file, "rt", encoding="utf-8") as f:
            for line in f:
                contents.append(line)
            for line_i in range(0,len(contents)):
                if contents[line_i]==(str(seq_n)+"\n") or contents[line_i]==("\ufeff1\n"):
                    matches = re.findall(r"(\d\d:\d\d:\d\d,\d\d\d)",contents[line_i + 1])
                    script_i = 2
                    script = ""
                    while contents[line_i + script_i] != "\n":
                        script += contents[line_i + script_i][:-1] + " "
                        script_i += 1
                    for lang in self.__voices:
                        if lang != "en":
                            script = clean_ssml_tags(script, True)
                        seq_dict[lang][seq_n] = {"script_start": matches[0],
                                        "script_end": matches[1],
                                        "script": script}
                    seq_n += 1
            self.__n_seq = seq_n - 1
        return seq_dict

    def __rebuild_dict(self):
        language = self.__language
        new_dict = {}
        n_seq_i = 1
        for seq_i in self.__seq_dict[language]:
            seq_script = self.__seq_dict[language][seq_i]["script"]
            seq_script = re.sub(r"\s\s+", " ", seq_script)
            if seq_script == "":
                continue
            ori_start = _to_seconds(self.__seq_dict[language][seq_i]["script_start"])
            ori_end = _to_seconds(self.__seq_dict[language][seq_i]["script_end"])
            ori_period = ori_end - ori_start
            script_splt = [seq_script]
            if seq_script[0] != "{" :
                seq_script = clean_ssml_tags(seq_script)
                script_splt = _split_script(seq_script, language)
            ori_len = len(seq_script)
            n_script_splt = len(script_splt)
            prev_end = ori_start
            for script in script_splt:
                script_ = script
                splt_len = len(script)
                splt_period = splt_len/ori_len * ori_period
                new_start = prev_end
                if script!="" and script[0] == "{":
                    script_ = json.loads(script)["display_name"]
                new_end = new_start + splt_period
                seq_dict = dict(
                    script=script_,
                    script_start=_to_time_str(new_start),
                    script_end=_to_time_str(new_end)
                )
                new_dict[n_seq_i] = seq_dict
                prev_end = new_end
                n_seq_i += 1
        return new_dict          
    
    def __seq_for_SRT(self, seq_n, op_dict=None):
        language = self.__language
        if op_dict == None:
            op_dict = self.__seq_dict[language]
        time_stamp = "%s --> %s"% (op_dict[seq_n]["script_start"], op_dict[seq_n]["script_end"])
        return "%s\n%s\n%s\n\n" % (str(seq_n), time_stamp, _xml_friendly.to_symbol(op_dict[seq_n]["script"]))

def clean_ssml_tags(script, remove_all=False):
    if remove_all:
        return re.sub(r"<.+?[\"'](.+?)[\"']>.+?<[/\w+].+?>","\g<1>",script)
    else:
        return re.sub(r"<[/?\w+].+?>"," ",script)

def sequence_convert(SEQ_CONVERT_RULES, script, seq_i, srt_obj):
    SEQ_CONVERT = SEQ_CONVERT_RULES["SEQ_CONVERT"]
    SRT_SEQ_CONVERT = SEQ_CONVERT_RULES["SRT_SEQ_CONVERT"]

    RULES = list(SEQ_CONVERT.keys())
    for RULE in RULES:
        if RULE.lower() in script.lower():
            _sequence_convert_toSRT(SRT_SEQ_CONVERT, script, seq_i, srt_obj)
            script = re.compile(r"\s*(<.+?[\"'].+?[\"']>)?(\s*%s\s*)(<[/\w+].+?>)?\s*" % RULE).sub(" %s " % SEQ_CONVERT[RULE], script)
    return script

def _sequence_convert_toSRT(SRT_SEQ_CONVERT, script, seq_i, srt_obj):
    RULES = list(SRT_SEQ_CONVERT.keys())
    for RULE in RULES:
        if RULE.lower() in script.lower():
            script = re.sub(RULE,SRT_SEQ_CONVERT[RULE], script)
            srt_obj.update_script(seq_i, script)

def _quotes_to_comma(script):
    return re.compile(r"([^=])\"\s?([^\s]+?)\s?\"").sub("\g<1>,\g<2>,", script)

def _split_script(script, language): # to create separate split functions for different languages !!!!!!!!!!!!!!!!!!!!!!!!!!!!
    if language == "en":
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
        logger.exception("_translate")
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
        logger.exception(text)
        print(error)
        print(text)
        sys.exit(-1)

    if "AudioStream" in response:
        with closing(response["AudioStream"]) as stream:
            output = os.path.join(output_fdr, file_name)
            try:
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                logger.exception("_polly_IO")
                print(error)
                sys.exit(-1)
            return output
    else:
        print("Could not stream audio")
        sys.exit(-1)

def _file_idx(file_name):
    return int(re.search(r"-(\d+)\.",file_name).group(1))

def cut_MP4(mp4_obj, srt_obj): # returns mp4s in subfolder
    try:
        clip = VideoFileClip(mp4_obj.get_path())
        output_fdr = mp4_obj.get_folder() + "\\" + mp4_obj.get_name() +"\\" + OUTPUT_FDR + "_VIDEOS\\"
        os.makedirs(output_fdr, exist_ok=True)
        num_seq = srt_obj.get_n_seq()
        for seq_i in range(1, num_seq + 1):#range(0, num_seq)
            script_start = srt_obj.get_seq("_NA_", seq_i)["script_start"]
            new_clip = None
            if seq_i == num_seq:#num_seq-1
                new_clip = clip.subclip(script_start)
            else:
                next_start = srt_obj.get_seq("_NA_", seq_i + 1)["script_start"]
                new_clip = clip.subclip(script_start, next_start)
            
            prev_end = script_start
            file_name = mp4_obj.get_name() + "-" + str(seq_i).zfill(3) + ".mp4"
            output_path = output_fdr + file_name
            new_clip.write_videofile(output_path, audio=False)
    except Exception:
        logger.exception(mp4_obj.get_path())

def to_Polly(srt_obj, voice_id, neural, SEQ_CONVERT_RULES, pptx=False):# returns mp3s in subfolder
    session = Session(
        aws_access_key_id = __AWS__.ID, 
        aws_secret_access_key = __AWS__.KEY, region_name="us-east-1")
    language = srt_obj.get_language()
    output_fdr = srt_obj.get_folder() + "\\" + srt_obj.get_name()[:-3] +"\\" + OUTPUT_FDR + "_%s\\" % language
    os.makedirs(output_fdr, exist_ok=True)
    for seq_i in range(1, srt_obj.get_n_seq()+1):
        script = _xml_friendly.to_xml(srt_obj.get_seq(language, seq_i)["script"])
        script = _quotes_to_comma(script)
        script = re.sub("_", "-", script)
        script = sequence_convert(SEQ_CONVERT_RULES, script, seq_i, srt_obj)

        if script!="" and script[0]!="{":
            if srt_obj.get_name()[-2:] == "en" and language!="en": # translate
                script = _translate(session, script, language) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                srt_obj.update_script(seq_i, script)
            file_name = srt_obj.get_name() + "-" + str(seq_i).zfill(3) + ".mp3"
            output_path = output_fdr + file_name
            print("\nCommunicating to AWS Polly")
            aud_out = _polly(session=session, output_fdr=output_fdr, file_name=file_name, script=script, voice_id=voice_id , neural=neural) # !!!!!!!!!
            print("Polly MP3 saved at %s" % (aud_out))
        else:
            if script == "":
                srt_obj.set_seq_end(seq_i, PAUSE_PERIOD)
            elif script!="" and script[0]=="{":
                srt_obj.set_seq_end(seq_i, TITLE_PERIOD)

def break_title(title):
    title_len = len(title)
    if title_len <= IDEAL_LENGTH:
        return title
    else:
        words = title.split(" ")
        ret_title = ""
        curr_line_len = 0
        for word in words:
            if ((curr_line_len + len(word)) >= IDEAL_LENGTH) and curr_line_len != 0:
                ret_title += "\n"
                curr_line_len = 0
            ret_title += " " + word
            curr_line_len += len(word)
        return ret_title

def _range(start, end, step):
    i = start
    while i < end:
        yield i
        i += step
    yield end

def composite_MP4(language, folder, vid_name, srt_obj):
    fade_color = [255,255,255]
    aud_clips = sorted(glob.glob(folder + "\\" + OUTPUT_FDR + "_%s\\" % language + "*.mp3"), key=_file_idx)
    aud_dict = {_file_idx(aud_clips[i]):aud_clips[i] for i in range(0, len(aud_clips))}
    try:
        vid_list = []
        total_duration = 0
        for seq_i in range(1, srt_obj.get_n_seq() + 1): # seq 1 is title
            seq_clip = None
            aud_clip = None

            script = srt_obj.get_seq(language, seq_i)["script"]
            fadeout = False
            try:
                nxt_script = srt_obj.get_seq(language, seq_i + 1)["script"]
            except KeyError:
                nxt_script = ""
                pass
            if nxt_script != "" and nxt_script[0] == "{":
                fadeout = True

            if script != "" and script[0] == "{":
                title = break_title(json.loads(script)["display_name"])
                if seq_i == 1 and language!="en":
                    title += "\n(%s)" % language
                title_clip = TextClip(txt=title, size=VIDEO_RES, method="label", font=FONT, color="black", bg_color="white", fontsize=FONT_SZ).set_duration("00:00:0%s" % (TITLE_PERIOD)).fadeout(duration=1, final_color=fade_color)
                vid_list.append(title_clip)
                seq_clip = title_clip
                aud_clip = title_clip
            else:
                vid_clips = sorted(glob.glob(folder + "\\" + OUTPUT_FDR + "_VIDEOS\\" + "*.mp4"), key=_file_idx)
                vid_clip = VideoFileClip(vid_clips[seq_i-1]).resize(height=VIDEO_RES[1])
                vid_idx = _file_idx(vid_clips[seq_i-1])
                if script != "":
                    aud_clip = AudioFileClip(aud_dict[vid_idx]).audio_fadein(0.01).audio_fadeout(0.01)
                    if (vid_clip.duration < aud_clip.duration):
                        vid_clip = vid_clip.set_duration(aud_clip.duration + PAUSE_PERIOD * 2)
                    vid_clip = vid_clip.set_audio(aud_clip)
                else:
                    if vid_clip.duration < 1:
                        vid_clip.duration = 1
                    aud_clip = vid_clip
                if fadeout:
                    vid_clip = vid_clip.fadeout(duration=1, final_color=fade_color)
                vid_list.append(vid_clip)
                seq_clip = vid_clip
                fadein = False
            seq_duration = seq_clip.duration
            aud_duration = aud_clip.duration
            seq_start = total_duration
            srt_obj.set_seq_start(seq_i, seq_start)
            srt_obj.set_seq_end(seq_i, aud_duration)
            total_duration += seq_duration

        composite = concatenate_videoclips(vid_list).resize(height=VIDEO_RES[1])
        composite.fps = 30
        composite_path = folder + "\\" + vid_name + "_%s_comp.mp4" % language
        composite.write_videofile(composite_path, audio_codec="aac")

        srt_obj.update_SRT()
        print("Job Complete")
        return composite_path
    except Exception:
        logger.exception("%s > MP4 build error" % vid_name)

def composite_PNGs(language, folder, vid_name, srt_obj):
    fade_color = [255,255,255]
    aud_clips = sorted(glob.glob(folder + "\\" + OUTPUT_FDR + "_%s\\" % language + "*.mp3"), key=_file_idx)
    aud_dict = {_file_idx(aud_clips[i]):aud_clips[i] for i in range(0, len(aud_clips))}

    try:    
        vid_list = []
        total_duration = 0

        for seq_i in range(1, srt_obj.get_n_seq() + 1): # seq 1 is title
            seq_clip = None
            aud_clip = None

            script = srt_obj.get_seq(language, seq_i)["script"]
            fadeout = False
            try:
                nxt_script = srt_obj.get_seq(language, seq_i + 1)["script"]
            except KeyError:
                nxt_script = ""
                pass
            if nxt_script != "" and nxt_script[0] == "{":
                fadeout = True

            if script != "" and script[0] == "{":
                title = break_title(json.loads(script)["display_name"])
                if seq_i == 1 and language!="en":
                    title += "\n(%s)" % language
                title_clip = TextClip(txt=title, size=VIDEO_RES, method="label", font=FONT, color="black", bg_color="white", fontsize=FONT_SZ).set_duration("00:00:0%s" % (TITLE_PERIOD)).fadeout(duration=1, final_color=fade_color)
                vid_list.append(title_clip)
                seq_clip = title_clip
                aud_clip = title_clip
            else:
                slide_pngs = sorted(glob.glob(folder + "\\images\\" + "*.png"), key=_file_idx)
                slide_clip = ImageClip(slide_pngs[seq_i-1])
                slides_idx = _file_idx(slide_pngs[seq_i-1]) + 1
                try:
                    aud_clip = AudioFileClip(aud_dict[slides_idx]).audio_fadein(0.01).audio_fadeout(0.01)
                    slide_clip = slide_clip.set_duration(aud_clip.duration + PAUSE_PERIOD * 2).set_audio(aud_clip)
                except KeyError:
                    slide_clip = slide_clip.set_duration(PAUSE_PERIOD * 2)
                    aud_clip = slide_clip
                    pass
                if fadeout:
                    slide_clip = slide_clip.fadeout(duration=1, final_color=fade_color)
                vid_list.append(slide_clip)
                seq_clip = slide_clip
                fadein = False
            seq_duration = seq_clip.duration
            aud_duration = aud_clip.duration
            seq_start = total_duration
            srt_obj.set_seq_start(seq_i, seq_start)
            srt_obj.set_seq_end(seq_i, aud_duration)
            total_duration += seq_duration
        composite = concatenate_videoclips(vid_list).resize(height=VIDEO_RES[1])
        composite.fps = 30
        composite_path = folder + "\\" + vid_name + "_%s_comp.mp4" % language
        composite.write_videofile(composite_path, audio_codec="aac")

        srt_obj.update_SRT()
        print("Job Complete")
        return composite_path
    except Exception:
        logger.exception("%s > MP4 build error" % vid_name)

def composite_headshot(tar_folder, vid_path, vid_name, srt_obj):
    fade_color = [255,255,255]
    script = srt_obj.get_seq("_NA_", 1)["script"]
    title = break_title(json.loads(script)["display_name"])
    title_clip = TextClip(txt=title, size=HS_VIDEO_RES, method="label", font=FONT, color="black", bg_color="white", fontsize=FONT_SZ).set_duration("00:00:0%s" % (TITLE_PERIOD)).fadeout(duration=1, final_color=fade_color)
    vid_list = [title_clip,VideoFileClip(vid_path).resize(height=HS_VIDEO_RES[1])]

    composite = concatenate_videoclips(vid_list).resize(width=VIDEO_RES[0])
    composite.fps = 30
    composite_path = tar_folder + "\\" + vid_name + "_comp.mp4"
    composite.write_videofile(composite_path, audio_codec="aac")

    update_HS_srt(srt_obj)
    print("Job Complete")
    return composite_path

def update_HS_srt(srt_obj):
    srt_obj.set_seq_end(1,TITLE_PERIOD)
    srt_obj.push_seq(1,TITLE_PERIOD)
    srt_obj.update_SRT()
