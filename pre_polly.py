from _checks import *
from _get_by_type import *
from _video_JSON import VidJSON, VidsJSON
from _to_github import *
import glob
import argparse
import os

SKIP = True
VIDEOS_JSON_FILE = "videos.json"
VIDEOS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),VIDEOS_JSON_FILE)
VIDEOS_FDR = "VIDEOS\\"
FOLDERS = glob.glob("%s*\\" % (VIDEOS_FDR))
STATUS = "pre"
FRESH = not vids_json_exists(VIDEOS_JSON_PATH,True)

vids_obj = VidsJSON(VIDEOS_JSON_PATH, FRESH)
changes_lst = vids_obj.get_changes_lst()
vids_body_dict = vids_obj.get_body_dict()
change_log = {}
end_msg = "Pre-Polly Process Complete."

for folder_i in range(0, len(FOLDERS)):
    VIDEO_i = vids_obj.get_nxt_vid_i()

    FOLDER_PATH = FOLDERS[folder_i]
    json_paths = get_paths_by_typ(FOLDER_PATH,"json")
    vid_obj = None
    status = STATUS
    if json_paths == None:
        continue
    if not valid_vid_json(json_paths[0]):
        continue
    else: # check for changes
        json_path = json_paths[0]
        vid_obj = VidJSON(json_path, VIDEO_i)

        vid_curr_edit = os.path.getmtime(json_path)
        if FRESH:
            change_log[VIDEO_i] = "FRESH"
        else:
            try:
                vids_saved_edit = vids_body_dict[str(vid_obj.get_video_i())]["meta"]["last_edit"]
                saved_prepolly = vids_obj.get_body_dict()[str(vid_obj.get_video_i())]["meta"]["pre_polly_id"]
                curr_prepolly = vid_obj.get_pre_id()
                if vids_saved_edit != vid_curr_edit:
                    change_log[vid_obj.get_video_i()] = "UPDATE"
                    if (curr_prepolly != saved_prepolly) and curr_prepolly != "":
                        status = "video"
                else:
                    end_msg += " No changes detected."
                    continue
            except Exception:
                change_log[VIDEO_i] = "FRESH"

        vid_obj.set_status(status)
        vid_obj.update_JSON()
        end_msg += " Change log:"
        if vid_obj.get_video_i() not in changes_lst:
            changes_lst.append(vid_obj.get_video_i())
        vid_obj.set_lst_edt(os.path.getmtime(json_path))
        vids_obj.set_vid_obj(vid_obj)
          
vids_obj.set_status(STATUS)
vids_obj.set_changes(changes_lst)
vids_obj.to_JSON()

print(end_msg)
for log_i in change_log:
    print("\t%s: %s" % (log_i, change_log[log_i]))
# if len(changes_lst) > 0:
#     commit_msg = "Pre-Polly. Changes Made: [%s]" % ", ".join(map(str, changes_lst))
#     commit_n_push([VIDEOS_JSON_FILE],commit_msg)