from _checks import *
from _get_by_type import *
from _video_JSON import VidJSON, VidsJSON, dict_to_json
from _movie_to_polly import *
from _pptx_to_video import pptx_to_ingreds
from _to_youtube import dl_vid
from _to_github import *
from _to_S3 import upload_s3
from __CONSTS__ import S3_bucket

import glob
import argparse
import os
import sys
import re
import shutil
import time
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--clean", dest="cleanup", action="store_true", help="Delete files after process.")
parser.add_argument("--keep", dest="cleanup", action="store_false", help="Keeps files after process.")
parser.set_defaults(cleanup=False)

CLEANUP = parser.parse_args().cleanup
VIDEOS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"videos.json")
VIDEOS_FDR = "VIDEOS\\"
os.makedirs(VIDEOS_FDR, exist_ok=True)
FOLDERS = glob.glob("%s*\\" % (VIDEOS_FDR))
STATUS = "post"
FRESH = not vids_json_exists(VIDEOS_JSON_PATH,False) # videos.json must exist
LANGUAGES = ["uk", "zh"] # available: ["us", "uk", "zh", "pt", "es"]


def sub_process(typ, folder, vids_obj):
    folder_name = re.search(r"\\(\d+)", folder).group(1)
    mp4_obj = None
    srt_obj = None
    vid_obj = None

    try:
        vid_obj = VidJSON(get_paths_by_typ(folder, "json")[0], folder_name)
        vid_args = vid_obj.get_vid_args()
        vid_name = re.search("-[\d]{4}-(.*)",vid_args["title"]).group(1)
        if typ == "YT":
            srt_obj = ToPollySRT(folder, LANGUAGES)
            mp4_obj = ToPollyMP4(folder)
            cut_MP4(mp4_obj,srt_obj)
        else:
            pptx_path = vid_obj.get_pptx_path()
            pptx_to_ingreds(pptx_path, folder) #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            srt_obj = ToPollySRT(folder, LANGUAGES)

        voice_id = vid_args["voice_id"]
        description = vid_args["description"]
        AVAIL_VOICES = srt_obj.get_languages() # dictionary of available voices in _movie_to_polly
        post_id_dict = vid_obj.get_post_id_dict()

        for lang in LANGUAGES:
            neural = AVAIL_VOICES[lang]["neural"]
            lang_code = AVAIL_VOICES[lang]["lang_code"]
            avail_voice_ids = AVAIL_VOICES[lang]["ids"]
            polly_voice_id = avail_voice_ids[voice_id % len(avail_voice_ids)]
            print("\n%s" % polly_voice_id)
            to_Polly(srt_obj, lang, polly_voice_id, neural) #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            if typ == "YT":
                comp_path = composite_MP4(lang, folder, vid_name, description)
            else:
                comp_path = composite_PNGs(lang, folder, vid_name, description)

            S3_path = re.sub("-", "/", vid_args["title"]) + ".mp4" 
            upload_s3(comp_path, S3_bucket, S3_path)
            post_id_dict[lang] = S3_path
    except Exception as e:
        try:
            raise e
        except:
            pass
        
        traceback.print_exc()
        return False # add failed to change list

    vid_obj.set_post_id_dict(post_id_dict)
    vid_obj.set_status(STATUS)
    vids_obj.set_vid_obj(vid_obj)
    if not CLEANUP:
        vid_obj.update_JSON()
    return True

def main():
    _ERROR = False
    _Error_msg = None

    vids_obj = VidsJSON(VIDEOS_JSON_PATH, FRESH)

    updated_ch_lst = []
    changes_lst = vids_obj.get_changes_lst()
    body_dict = vids_obj.get_body_dict()

    for folder_id in changes_lst:
        folder_id = str(folder_id)
        folder_path = os.path.join(VIDEOS_FDR,folder_id) + "\\"
        vid_dict = body_dict[folder_id]
        os.makedirs(folder_path, exist_ok=True)
        dict_to_json(vid_dict,os.path.join(folder_path,"%s.json" % (folder_id)))

        success = False
        if vid_dict["meta"]["status"] == "pptx":
            print("\nPPTX to VIDEO PROCESS")
            success = sub_process("PPTX", folder_path, vids_obj)
        else:
            pre_id = vid_dict["meta"]["pre_polly_id"]
            if pre_id != "":
                print("\nYT to VIDEO PROCESS")
                vid_name = re.search("-[\d]{4}-(.*)",vid_dict["title"]).group(1)
                # download video and srt into VIDEOS_FDR\folder_id
                dl_vid(pre_id,folder_path,folder_id, vid_name)
                success = sub_process("YT", folder_path, vids_obj)
        if not success:
            updated_ch_lst.append(folder_id)        
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

        print("\nPost-Polly Process Complete. Changes Made: %s" % (len(changes_lst) - len(updated_ch_lst)))
        # if (len(changes_lst) - len(updated_ch_lst)) > 0:
        #     commit_msg = "Post-Polly. Changes Left: [%s]" % ", ".join(map(str, updated_ch_lst))
        #     paths_lst = glob.glob("POST_SRT\\")
        #     paths_lst.append(VIDEOS_JSON_FILE)
        #     commit_n_push(paths_lst,commit_msg)

main()
