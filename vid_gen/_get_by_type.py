import glob
import os

def get_paths_by_typ(fdr_path,typ):
    paths = glob.glob(fdr_path + "\\*.%s" % (typ))
    ret_paths = [path for path in paths if not os.path.basename(path).startswith("~$")]
    # if (len(paths)==0):
    #     raise Exception ("No .%s file found in \\%s." % (typ, fdr_path))    
    return ret_paths
