from checks import *
from get_by_type import *
from video_JSON import VidJSON, VidsJSON
from to_youtube import *
import glob
import argparse
import os

YT_SESSION = get_authenticated_service()

SKIP = True
VIDEOS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"videos.json")
VIDEOS_FDR = "VIDEOS\\"
FOLDERS = glob.glob("%s*\\" % (VIDEOS_FDR))
STATUS = "pre"
FRESH = not vids_json_exists(VIDEOS_JSON_PATH,True)
_ERROR = False
_ERROR_msg = None

vids_obj = VidsJSON(VIDEOS_JSON_PATH, FRESH)
changes_lst = vids_obj.get_dict()["log"]["changes"]

for folder_i in range(0, len(FOLDERS)):
    VIDEO_i = vids_obj.get_dict()["log"]["nxt_vid_i"]
    vids_obj.reset_vid_i()
    FOLDER_PATH = FOLDERS[folder_i]
    json_paths = get_paths_by_typ(FOLDER_PATH,"json")
    mp4_paths = get_paths_by_typ(FOLDER_PATH,"mp4")
    vid_obj = None
    if json_paths == None or mp4_paths == None:
        continue
    if not valid_vid_json(json_paths[0],SKIP):
        continue
    else: # check time
        mp4_path = mp4_paths[0]
        json_path = json_paths[0]
        vid_obj = VidJSON(json_path, VIDEO_i)

        curr_edit_time = vid_obj.get_lst_edt()
        curr_status = vid_obj.get_status()
        
        json_edit_time = os.path.getmtime(json_path)
        if json_edit_time > curr_edit_time:
            curr_status = "json"
            curr_edit_time = json_edit_time
        mp4_edit_time = os.path.getmtime(mp4_path)
        if mp4_edit_time > curr_edit_time:
            curr_status = "mp4"
            curr_edit_time = mp4_edit_time
        if vid_obj.get_lst_edt() >= curr_edit_time:
            continue
        
        pre_polly_id = vid_obj.get_pre_id()
        try:
            if pre_polly_id == "": # new upload
                pre_polly_id = upload_vid(YT_SESSION, mp4_path, vid_obj.get_yt_args())
            else: # update
                if curr_status == "json": # update video details
                    update_vid_details(YT_SESSION,pre_polly_id,vid_obj.get_yt_args())
                    curr_status = vid_obj.get_status()
                else: # update mp4
                    dl_captions(YT_SESSION,pre_polly_id,FOLDER_PATH)
                    del_vid(YT_SESSION,pre_polly_id)
                    pre_polly_id = upload_vid(YT_SESSION, mp4_path, vid_obj.get_yt_args())
        except HttpError as e:
            if SKIP:
                print(e.args[0] + ". Folder skipped.")
            else:
                _ERROR = True
                _ERROR_msg = e.args[0]
        vid_obj.set_pre_id(pre_polly_id)
        vid_obj.set_status(curr_status)
        vid_obj.set_lst_edt(curr_edit_time)
        vid_obj.update_JSON()
        changes_lst.append(VIDEO_i)
        vids_obj.set_vid_obj(vid_obj)
        if _ERROR:
            break

vids_obj.set_status(STATUS)
vids_obj.set_changes(changes_lst)
vids_obj.to_JSON()

if _ERROR:
    print(_ERROR_msg)
else:   
    print("Pre-Polly Process Complete. Changes Made: %s" % (len(changes_lst)))