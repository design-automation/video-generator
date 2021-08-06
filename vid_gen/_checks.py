import os
import json
import glob

def _valid_json(path): # checks if json can be loaded.
    err_msg = "Invalid JSON at: %s" % (path)
    try:
        with open(path) as json_f:
            test = json.load(json_f)
            return True
    except IOError:
        print(err_msg)
        raise

def vids_json_exists(path,skip): # to check videos.json
    check = os.path.isfile(path)
    err_msg = "%s does not exist." % (path)
    if not check:
        if not skip:
            raise Exception(err_msg)
        else:
            print(err_msg + " New file will be created at location.")
    return check
