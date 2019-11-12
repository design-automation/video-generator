from _checks import *
from _get_by_type import *
from _video_JSON import VidJSON, VidsJSON, dict_to_json
from _movie_to_polly import *
from _to_youtube import dl_vid
from _to_github import *
import glob
import argparse
import os
import sys
import re
import shutil
import time

parser = argparse.ArgumentParser()
parser.add_argument("--clean", dest="cleanup", action="store_true", help="Delete files after process.")
parser.add_argument("--keep", dest="cleanup", action="store_false", help="Keeps files after process.")
parser.set_defaults(cleanup=False)

SKIP = False
CLEANUP = parser.parse_args().cleanup
VIDEOS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"videos.json")
VIDEOS_FDR = "VIDEOS\\"
os.makedirs(VIDEOS_FDR, exist_ok=True)
FOLDERS = glob.glob("%s*\\" % (VIDEOS_FDR))
STATUS = "post"
FRESH = not vids_json_exists(VIDEOS_JSON_PATH,False) # videos.json must exist
LANGUAGES = ["uk", "zh"] # available: ["us", "uk", "zh", "pt", "es"]

_ERROR = False
_Error_msg = None

vids_obj = VidsJSON(VIDEOS_JSON_PATH, FRESH)

updated_ch_lst = []
changes_lst = vids_obj.get_changes_lst()
body_dict = vids_obj.get_body_dict()
error_dict = {}

folder_paths = []
for folder_id in changes_lst:
    folder_id = str(folder_id)
    folder_path = os.path.join(VIDEOS_FDR,folder_id) + "\\"
    vid_dict = body_dict[folder_id]
    pre_id = vid_dict["meta"]["pre_polly_id"]
    vid_name = re.search("-[\d]{4}-(.*)",vid_dict["title"]).group(1)
    os.makedirs(folder_path, exist_ok=True)
    
    dict_to_json(vid_dict,os.path.join(folder_path,"%s.json" % (folder_id)))
    # download video and srt into VIDEOS_FDR\folder_id
    folder_paths.append(folder_path)
    dl_vid(pre_id,folder_path,folder_id, vid_name) # triggers error
   
for folder in folder_paths:
    folder_name = re.search(r"\\(\d+)", folder).group(1)
    mp4_obj = None
    srt_obj = None
    vid_obj = None

    try:
        mp4_obj = ToPollyMP4(folder)
        srt_obj = ToPollySRT(folder, LANGUAGES)
        vid_obj = VidJSON(get_paths_by_typ(folder, "json")[0], folder_name)
        if vid_obj.get_status() != "video":
            error_dict[vid_obj.get_video_i] = "no video"
        
        # Polly
        vid_name = mp4_obj.get_name()
        cut_MP4(mp4_obj,srt_obj)

        vid_args = vid_obj.get_vid_args()
        voice_id = vid_args["voice_id"]
        description = vid_args["description"]
        AVAIL_VOICES = srt_obj.get_languages() # dictionary of available voices in _movie_to_polly

        for lang in LANGUAGES:
            neural = AVAIL_VOICES[lang]["neural"]
            lang_code = AVAIL_VOICES[lang]["lang_code"]
            avail_voice_ids = AVAIL_VOICES[lang]["ids"]
            polly_voice_id = avail_voice_ids[voice_id % len(avail_voice_ids)]
            print(polly_voice_id)
            to_Polly(srt_obj, lang, polly_voice_id, neural)
            comp_path = composite_MP4(lang, folder, vid_name, description)
            # Upload 
            # Upload to S3 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # if post_id != "":
            #     del_vid(YT_SESSION, post_id)
            # post_id = upload_vid(YT_SESSION,comp_path,vid_obj.get_vid_args())

    except Exception as e:
        updated_ch_lst.append(folder_name) # add failed to change list
        if SKIP:
            print (e.args[0] + " Folder skipped.")
        else:
            error_dict[vid_obj.get_video_i] = srt_obj.get_full_dict()
            raise e
            _ERROR = True
            _ERROR_msg = e

    if _ERROR or vid_obj == None:
        break
    else:
        # vid_obj.set_post_id(post_id)
        if folder_name not in updated_ch_lst:
            vid_obj.set_status(STATUS)
        vids_obj.set_vid_obj(vid_obj)
        if not CLEANUP:
            vid_obj.update_JSON()

with open("error_log.json", "w", encoding="utf-8") as json_f:
    json.dump(error_dict, json_f, ensure_ascii=False, indent=4)

if len(updated_ch_lst) == 0:
    vids_obj.set_status(STATUS)
vids_obj.set_changes(updated_ch_lst)
vids_obj.to_JSON()

if CLEANUP:
    print("\nCleanup initiated. Removing Processed Files")
    fdrs = glob.glob(VIDEOS_FDR + "*\\")
    for fdr in fdrs:
        shutil.rmtree(fdr)
else:
    print("\nCleanup skipped. Include --clean to remove processed files.")

if _ERROR:
    print(_ERROR_msg)
else:   
    print("\nPost-Polly Process Complete. Changes Made: %s" % (len(changes_lst) - len(updated_ch_lst)))
    # if (len(changes_lst) - len(updated_ch_lst)) > 0:
    #     commit_msg = "Post-Polly. Changes Left: [%s]" % ", ".join(map(str, updated_ch_lst))
    #     paths_lst = glob.glob("POST_SRT\\")
    #     paths_lst.append(VIDEOS_JSON_FILE)
    #     commit_n_push(paths_lst,commit_msg)