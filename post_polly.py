from _checks import *
from _get_by_type import *
from _video_JSON import VidJSON, VidsJSON, dict_to_json
from _movie_to_polly import *
from _to_youtube import *
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
YT_SESSION = get_authenticated_service()

SKIP = True
CLEANUP = parser.parse_args().cleanup
VIDEOS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"videos.json")
VIDEOS_FDR = "VIDEOS\\"
os.makedirs(VIDEOS_FDR, exist_ok=True)
FOLDERS = glob.glob("%s*\\" % (VIDEOS_FDR))
STATUS = "post"
FRESH = not vids_json_exists(VIDEOS_JSON_PATH,False) # videos.json must exist

_ERROR = False
_Error_msg = None

vids_obj = VidsJSON(VIDEOS_JSON_PATH, FRESH)
vids_dict = vids_obj.get_dict()

updated_ch_lst = []
changes_lst = vids_dict["log"]["changes"]
body_dict = vids_dict["body"]

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
    post_id = ""
    try:
        mp4_obj = ToPollyMP4(folder)
        srt_obj = ToPollySRT(folder)
        vid_obj = VidJSON(get_paths_by_typ(folder, "json")[0], folder_name)
        post_id = vid_obj.get_post_id()

        if vid_obj.get_status() != "srt":
            err_msg = "Changed video in %s has not been labelled 'srt'" % (folder)
            raise Exception(err_msg)
        
        # Polly
        vid_name = mp4_obj.get_name()
        cut_MP4(mp4_obj,srt_obj)
        to_Polly(srt_obj)

        comp_path = composite_MP4(folder,vid_name,vid_obj.get_yt_args()["description"])
        # Upload
        if post_id != "":
            del_vid(YT_SESSION, post_id)
        post_id = upload_vid(YT_SESSION,comp_path,vid_obj.get_yt_args())

    except Exception as e:
        updated_ch_lst.append(folder_name) # add failed to change list
        if SKIP:
            print (e.args[0] + " Folder skipped.")
        else:
            _ERROR = True
            _ERROR_msg = e.args[0]

    if _ERROR or vid_obj == None:
        break
    else:
        vid_obj.set_post_id(post_id)
        if folder_name not in updated_ch_lst:
            vid_obj.set_status(STATUS)
        vids_obj.set_vid_obj(vid_obj)
        if not CLEANUP:
            vid_obj.update_JSON()

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
    if (len(changes_lst) - len(updated_ch_lst)) > 0:
        commit_msg = "Post-Polly. Changes Left: [%s]" % ", ".join(map(str, updated_ch_lst))
        commit_n_push([VIDEOS_JSON_FILE],commit_msg)