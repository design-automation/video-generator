import sys, os
#--------------------------------------------------------------------------------------------------
if len(sys.argv) != 3:
    raise Exception('Usage: python ./vid_generator.py input_path run_steps')
if not os.path.exists(sys.argv[1]):
    raise Exception('Path does not exist: ' + sys.argv[1])
if not os.path.exists(os.path.join(sys.argv[1], '__SETTINGS__.py')):
    raise Exception('Path does not contain __SETTINGS__.py: ' + sys.argv[1])
INPUT_PATH = os.path.normpath(sys.argv[1])
RUN_STEP = int(sys.argv[2])
RUN_STATUS = ["\nGENERATING INGREDIENTS\n", "\nGENERATING MP4\n"]
sys.path.append(INPUT_PATH)
#--------------------------------------------------------------------------------------------------
from _checks import *
from _get_by_type import *
from _polly_JSON import VidsJSON, Video
import glob
import argparse
from _pptx_to_video import pptx_to_ingreds
from _to_S3 import upload_s3
from _movie_to_polly import *
import traceback
from __SETTINGS__ import S3_MOOC_FOLDER, S3_BUCKET, S3_VIDEOS_FOLDER, LANGUAGES
#--------------------------------------------------------------------------------------------------
DEBUG_status = False
DEBUG = dict(
    section="w1",
    subsection="s2",
    unit="u2"
)
#--------------------------------------------------------------------------------------------------

def main():
    with open("errors.log" , "w") as error_f:
        error_f.write("")

    change_log = {}
    end_msg = "To-Polly Process Complete."  
    SECTIONS = glob.glob(os.path.join(INPUT_PATH, 'Course', '*\\'))

    range_arr = range(RUN_STEP, RUN_STEP + 1)
    if RUN_STEP == 2:
        range_arr = range(RUN_STEP)
    for run_i in range_arr: # 0 = ingredients only. 1 = MP4
        print(RUN_STATUS[run_i])
        # SECTIONS
        for section in SECTIONS:
            if DEBUG_status and os.path.basename(section[:-1]) != DEBUG["section"]:
                continue
            print('- ', section)
            SUBSECTIONS = glob.glob(os.path.join(section, '*\\'))

            # SUBSECTIONS
            for subsection in SUBSECTIONS:
                if DEBUG_status and os.path.basename(subsection[:-1]) != DEBUG["subsection"]:
                    continue
                print('-- ', subsection)
                UNITS = glob.glob(os.path.join(subsection, '*\\'))

                # UNITS
                for unit in UNITS:
                    if DEBUG_status and os.path.basename(unit[:-1]) != DEBUG["unit"]:
                        continue
                    print('--- ', unit)

                    unit = unit[:-1]
                    vid_files = get_paths_by_typ(unit, "pptx")
                    vid_files.extend(get_paths_by_typ(unit, "mp4"))
                    if vid_files == None:
                        continue
                    json_path = os.path.join(unit, "videos.json")
                    FRESH = not vids_json_exists(json_path,True)
                    vids_obj = VidsJSON(INPUT_PATH, json_path, FRESH)

                    # VIDEOS
                    for vid_file in vid_files:
                        print('---- ', vid_file)

                        vid_obj = Video(INPUT_PATH, vid_file)
                        id = vid_obj.get_file_name()
                        pp_curr_edit = vid_obj.get_pre_polly_edit()
                        pp_last_edit = vids_obj.get_pre_polly_edit(id)
                        vids_obj_edit = vids_obj.get_last_edit()
                        change = -1
                        success = False
                        if pp_curr_edit > pp_last_edit and pp_curr_edit > vids_obj_edit:
                            print("\nChange detected for %s. Generating videos for all languages.\n" % vid_obj.get_pre_polly_path())
                            change = 0  # gen all languages
                        else:
                            for lang in LANGUAGES:
                                lang_curr_modified = vid_obj.get_srt_edit(lang)
                                lang_last_modified = vids_obj.get_srt_edit(lang,id)
                                if lang_curr_modified > lang_last_modified and lang_curr_modified > vids_obj_edit:
                                    if lang == "en":
                                        change = 0
                                        break
                                    else:
                                        change = 1 # gen specific language
                                elif lang_curr_modified == -1:
                                    if lang == "en" and vid_obj.get_ext == "mp4":
                                        raise Exception (vid_obj.get_file_name() + "_en.srt does not exist")
                                    else:
                                        change = 1
                                else:
                                    print("\nNo change for %s\\%s_%s.srt\n" % (vid_obj.get_base_dir(), vid_obj.get_file_name(), lang))
                                    continue # no change
                                # change == 1
                                success = _generate_video(run_i, vid_obj, lang, change)
                                if not success:
                                    break
                        if change == 0:
                            success = _generate_all(run_i, vid_obj)
                        if success:
                            vids_obj.set_vid_obj(vid_obj)
                        if not DEBUG_status and change != -1 and run_i==1:
                            shutil.rmtree(path=vid_obj.get_base_dir() + "\\" + vid_obj.get_file_name(), ignore_errors=True)

                    # write to JSON file
                    if run_i == 1:
                        vids_obj.to_JSON()
#--------------------------------------------------------------------------------------------------
def _generate_all(run_i, vid_obj):
    success = False
    for lang in LANGUAGES:
        success = _generate_video(run_i, vid_obj, lang, 0)
        if not success:
            print("\nError occured. Process Terminated.")
            break
    return success
#--------------------------------------------------------------------------------------------------
def _generate_video(run_i, vid_obj, language, change):
    print("\nGenerating %s video for %s\n" % (language, vid_obj.get_pre_polly_path()))
    try:
        vid_ext = vid_obj.get_ext()
        out_folder = "%s\\%s" % (vid_obj.get_base_dir(), vid_obj.get_file_name())
        os.makedirs(out_folder, exist_ok=True)
        if vid_ext == "pptx" and (language=="en" or change == 1): # break once
            pptx_to_ingreds(run_i, vid_obj.get_pre_polly_path(), out_folder) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        srt_path = vid_obj.get_srt_path(language)
        if not os.path.exists(srt_path):
            srt_path = vid_obj.get_srt_path("en")
        srt_obj = ToPollySRT(srt_path,language)

        vid_obj.set_vid_args(srt_obj)
        vid_args = vid_obj.get_vid_args()
        vid_name = vid_args["video_file_name"]

        voice_id = int(vid_args["voice"])
        
        AVAIL_VOICES = srt_obj.get_voices()
        neural = AVAIL_VOICES[language]["neural"]
        lang_code = AVAIL_VOICES[language]["lang_code"]
        avail_voice_ids = AVAIL_VOICES[language]["ids"]
        polly_voice_id = avail_voice_ids[voice_id % len(avail_voice_ids)]
        print("\n%s" % polly_voice_id)

        if vid_ext == "mp4":
            try:
                mp4_type = json.loads(srt_obj.get_seq("_NA_", 0)["script"])["type"]
                if mp4_type == "headshot" and run_i != 0:
                    comp_path = composite_headshot(vid_obj.get_pre_polly_path(), vid_name, srt_obj)
            except KeyError: # not headshot video
                if run_i == 0:
                    to_Polly(srt_obj, polly_voice_id, neural)
                else:
                    if (language=="en" or change == 1):
                        mp4_obj = ToPollyMP4(vid_obj.get_pre_polly_path())
                        cut_MP4(mp4_obj,srt_obj) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    comp_path = composite_MP4(language, out_folder, vid_name, srt_obj)
        else:
            if run_i == 0:
                to_Polly(srt_obj, polly_voice_id, neural, True)
            else:
                comp_path = composite_PNGs(language, out_folder, vid_name, srt_obj)
      
        if run_i == 1:
            S3_path = "%s/%s/%s_%s.mp4" % (S3_MOOC_FOLDER, S3_VIDEOS_FOLDER, re.sub("-", "/", vid_args["video_file_name"]), language)
            upload_s3(comp_path, S3_BUCKET, S3_path)
            print("\nUploaded to S3")

            vid_obj.set_srt_edit(language, os.path.getmtime(vid_obj.get_srt_path(language)))
            vid_obj.set_srt_edit("en", os.path.getmtime(vid_obj.get_srt_path("en")))
            vid_obj.set_pre_polly_edit(os.path.getmtime(vid_obj.get_pre_polly_path()))
        return True
    except Exception as e:
        try:
            raise e
        except Exception:
            pass
        if DEBUG_status:
            raise e
        traceback.print_exc()
        return False
#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
