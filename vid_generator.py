from _checks import *
from _get_by_type import *
from _polly_JSON import VidsJSON, Video
import glob
import argparse
import os
from __CONSTS__ import LANGUAGES, COURSE_PATH, EDX_COURSE, S3_bucket, S3_folder
from _pptx_to_video import pptx_to_ingreds
from _to_S3 import upload_s3
from _movie_to_polly import *
import traceback

def main():
    change_log = {}
    end_msg = "To-Polly Process Complete."  
    SECTIONS = glob.glob("%s*\\" % COURSE_PATH)
    # loop through sections in MOOC path
    for section in SECTIONS:
        SUBSECTIONS = glob.glob("%s*\\" % section)
        for subsection in SUBSECTIONS:
            UNITS = glob.glob("%s*\\" % subsection)
            for unit in UNITS:
                unit = unit[:-1]
                vid_files = get_paths_by_typ(unit, "pptx")
                vid_files.extend(get_paths_by_typ(unit, "mp4"))
                if vid_files == None:
                    continue
                json_path = os.path.join(unit, "videos.json")
                FRESH = not vids_json_exists(json_path,True)
                vids_obj = VidsJSON(json_path, FRESH)
                for vid_file in vid_files:
                    vid_obj = Video(vid_file)
                    id = vid_obj.get_file_name()
                    pp_curr_edit = vid_obj.get_pre_polly_edit()
                    pp_last_edit = vids_obj.get_pre_polly_edit(id)
                    change = -1
                    success = False
                    if pp_curr_edit > pp_last_edit:
                        change = 0  # gen all languages
                    for lang in LANGUAGES:
                        lang_curr_modified = vid_obj.get_srt_edit(lang)
                        lang_last_modified = vids_obj.get_srt_edit(lang,id)
                        if lang_curr_modified > lang_last_modified:
                            if lang == "uk" or lang == "us":
                                change = 0
                                break
                            else:
                                change = 1 # gen specific language
                        elif lang_curr_modified == -1:
                            if (lang == "uk" or lang == "us") and vid_obj.get_ext == "mp4":
                                raise Exception (vid_obj.get_file_name() + "_en.srt does not exist")
                            else:
                                change = 1
                        else:
                            print("\nNo change for %s\\%s\n" % (vid_obj.get_base_dir(), vid_obj.get_file_name()))
                            continue # no change
                        # change == 1
                        success = _generate_video(vid_obj, lang, change)
                        if not success:
                            break
                    if change == 0:
                        success = _generate_all(vid_obj)
                    if success:
                        vids_obj.set_vid_obj(vid_obj)
                    if change != -1:
                        shutil.rmtree(vid_obj.get_base_dir() + "\\" + vid_obj.get_file_name())
                vids_obj.to_JSON()

def _generate_all(vid_obj):
    success = False
    for lang in LANGUAGES:
        success = _generate_video(vid_obj, lang, 0)
        if not success:
            print("\nError occured. Process Terminated.")
            break
    return success

def _generate_video(vid_obj, language, change):
    try:
        vid_ext = vid_obj.get_ext()
        out_folder = "%s\\%s" % (vid_obj.get_base_dir(), vid_obj.get_file_name())
        os.makedirs(out_folder, exist_ok=True)
        if vid_ext == "pptx" and (language=="uk" or language=="us" or change == 1): # break once
            pptx_to_ingreds(vid_obj.get_pre_polly_path(), out_folder) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        srt_path = vid_obj.get_srt_path(language)
        if vid_obj.get_srt_edit(language) == -1:
            srt_path = vid_obj.get_srt_path("en")
        srt_obj = ToPollySRT(srt_path,language)

        vid_obj.set_vid_args(srt_obj)
        vid_args = vid_obj.get_vid_args()
        vid_name = vid_args["video_file_name"]

        if vid_ext == "mp4" and (language=="uk" or language=="us" or change == 1): # break once
            mp4_obj = ToPollyMP4(vid_obj.get_pre_polly_path())
            cut_MP4(mp4_obj,srt_obj) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        voice_id = int(vid_args["voice"])
        
        AVAIL_VOICES = srt_obj.get_voices()
        neural = AVAIL_VOICES[language]["neural"]
        lang_code = AVAIL_VOICES[language]["lang_code"]
        avail_voice_ids = AVAIL_VOICES[language]["ids"]
        polly_voice_id = avail_voice_ids[voice_id % len(avail_voice_ids)]
        print("\n%s" % polly_voice_id)

        if vid_ext == "mp4":
            to_Polly(srt_obj, polly_voice_id, neural)
            comp_path = composite_MP4(language, out_folder, vid_name, srt_obj)
        else:
            to_Polly(srt_obj, polly_voice_id, neural, True)
            comp_path = composite_PNGs(language, out_folder, vid_name, srt_obj)

        lang_append = language
        if language == "us" or language == "uk":
            lang_append = "en"
        
        S3_path = "%s/%s/%s_%s.mp4" % (EDX_COURSE, S3_folder, re.sub("-", "/", vid_args["video_file_name"]), lang_append)
        upload_s3(comp_path, S3_bucket, S3_path)
        print("\nUploaded to S3")

        vid_obj.set_srt_edit(language, os.path.getmtime(vid_obj.get_srt_path(language)))
        vid_obj.set_srt_edit("en", os.path.getmtime(vid_obj.get_srt_path("en")))
        return True
    except Exception as e:
        try:
            raise e
        except:
            pass
        
        traceback.print_exc()
        return False

main()