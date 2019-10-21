import glob
import re

def get_paths_by_typ(fdr_path,typ):
    paths = glob.glob(fdr_path + "\\*.%s" % (typ))
    if (len(paths)==0):
        raise Exception ("No .%s file found in \\%s." % (typ, fdr_path))    
    return paths
    