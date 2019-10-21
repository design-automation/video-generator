'''
===============================================
Basic file checks
-----------------------------------------------
Also handles whether Exception should be raised
returns boolean
===============================================
vids_json_exists(path, skip)

valid_vid_json(path, skip): shallow check
    title
    description
    tags
    ? meta

valid_vids_json(path): shallow check
    log
    body
===============================================
'''

import os
import json
import glob

VID_JSON_KEYS = ["title", "description"]
VIDS_JSON_KEYS = ["log", "body"]

def _valid_json(path, skip): # checks if json can be loaded.
    err_msg = "Invalid JSON at: %s" % (path)
    try:
        with open(path) as json_f:
            test = json.load(json_f)
            return True
    except IOError:
        if not skip:
            raise Exception (err_msg)
        else:
            print(err_msg + " Folder skipped.")

def valid_vid_json(path,skip):
    err_msg = "%s is invalid." % (path)
    check = False
    if not _valid_json(path, skip): return False
    with open(path) as json_f:
        vid_dict = json.load(json_f)
        for key in VID_JSON_KEYS:
            check = key in vid_dict
            if not check:
                err_msg += "key: '%s' does not exist. " % (key)
                if not skip:
                    raise Exception(err_msg)
                else:
                    print(err_msg + " Folder skipped.")
    return check

def vids_json_exists(path,skip): # to check videos.json
    check = os.path.isfile(path)
    err_msg = "%s does not exist." % (path)
    if not check:
        if not skip:
            raise Exception(err_msg)
        else:
            print(err_msg + " New file will be created at location.")
    return check

def valid_vids_json(path): # always raise
    _valid_json(path, False)
    err_msg = "%s is invalid." % (path)
    check = False
    with open(path) as json_f:
        vid_dict = json.load(json_f)
        for key in VID_JSON_KEYS:
            check = key in vid_dict
            if not check:
                err_msg += "key: '%s' does not exist. " % (key)
                raise Exception(err_msg)
    return check
