import subprocess
import os
import glob
import re
import functools
import logging
import zipfile
import sys

from bs4 import BeautifulSoup
from _movie_to_polly import _to_time_str, VIDEO_RES
import _xml_friendly

logging.basicConfig(filename='errors.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)
# unzipped_pptx > pptx > notesSlides > *.xml

def _pptx_notes_xml(pptx_path, tar_folder):
    print("Unzipping pptx file to xml notes")
    with zipfile.ZipFile(pptx_path, "r") as zip_ref:
        zip_ref.extractall(tar_folder)
    return os.path.join(tar_folder, "ppt", "notesSlides\\")
def _slide_idx(xml_path):
    return int(re.search(r"notesSlide(\d+)", xml_path).group(1))
def _clean_notes(notes):
    notes = notes.replace("“","\"").replace("”","\"") #.replace("’","'").replace("\u200c","")
    if notes!="" and notes[0]!="{":
        notes = notes.encode("ascii","ignore").decode("utf-8")
    return notes

def _pptx_to_SRT(pptx_path, tar_fdr):
    folder_path = _pptx_notes_xml(pptx_path, tar_fdr)
    print("Converting xml to srt")
    
    file_name = re.sub("\.pptx", "", os.path.basename(pptx_path))
    DEFAULT_TIME_BREAK = 3 #seconds
    xml_files = sorted(glob.glob(folder_path + "*.xml"), key=_slide_idx)

    slide_dict = {}
    n_slides = len(xml_files)
    for slide_i in range(0, n_slides):
        xml_file = xml_files[slide_i]
        with open (xml_file, "rt", encoding="utf-8") as xml_f:
            soup = BeautifulSoup(xml_f, "xml")
            note_segs = soup.findAll("a:r")
            slide_notes = ""
            for note_seg in note_segs:
                slide_notes += note_seg.find("a:t").text
                if slide_notes!="" and slide_notes[0] != "{":
                    slide_notes += " "
            slide_dict[str(slide_i+1)] = _clean_notes(slide_notes)
    with open(tar_fdr + "..\\..\\..\\" + file_name+"_en.srt", "wt", encoding="utf-8") as srt_f:
        for i in range(1, n_slides + 1):
            srt_f.write("%s\n" % str(i))
            srt_f.write("%s --> %s\n" % (_to_time_str((i-1)*DEFAULT_TIME_BREAK + 0.5), _to_time_str((i)*DEFAULT_TIME_BREAK + 0.5)))
            srt_f.write("%s\n" % slide_dict[str(i)])
            srt_f.write("\n")

def _libreXML_to_SRT(folder_path, tar_fdr):
    DEFAULT_TIME_BREAK = 5 #seconds
    xml_file = glob.glob(folder_path + "\\*.xml")[0]
    file_name = re.sub("\.xml", "", os.path.basename(xml_file))
    slide_dict = {}
    n_slides = 0
    with open (xml_file, "rt", encoding="utf-8") as xml_f:
        soup = BeautifulSoup(xml_f, "xml")
        all_slides = soup.findAll("div", attrs={"class": re.compile(r'dp[1-5]')})
        n_slides = len(all_slides)
        for slide_i in range(0, n_slides):
            slide = all_slides[slide_i]
            notes=""
            try:
                notesdiv = slide.find("div", id=re.compile(r'Notes*'))
                notes_lst = notesdiv.findAll("span")
                for note in notes_lst:
                    notes += note.text
            except AttributeError:
                notes = ""
            slide_dict[str(slide_i + 1)] = _clean_notes(notes)
    with open(tar_fdr + "\\" + file_name+"_en.srt", "wt", encoding="utf-8") as srt_f:
        for i in range(1, n_slides + 1):
            srt_f.write("%s\n" % str(i))
            srt_f.write("%s --> %s\n" % (_to_time_str((i-1)*DEFAULT_TIME_BREAK), _to_time_str((i)*DEFAULT_TIME_BREAK)))
            srt_f.write("%s\n" % slide_dict[str(i)])
            srt_f.write("\n")

def pptx_to_ingreds(run_i, pptx_path, tar_folder):
    pptx_abs_path =  os.path.abspath(pptx_path)
    folder = os.path.abspath(tar_folder)
    file_name = re.sub("\.pptx", "", os.path.basename(pptx_abs_path))
    image_fdr = os.path.abspath(os.path.join(folder, "images\\"))
    unzip_fdr = os.path.abspath(os.path.join(folder, "unzipped_pptx\\"))
    os.makedirs(image_fdr, exist_ok=True)
    os.makedirs(unzip_fdr, exist_ok=True)
    sz = "%sx%s" % VIDEO_RES

    try:
        if run_i == 0:
            _pptx_to_SRT(pptx_abs_path, unzip_fdr)
        else:
            print("Converting pptx file to pdf")
            subprocess.run([os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'python.exe'), os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'unoconv'), '-f', "pdf", "-o", "%s\\%s.pdf" % (folder, file_name),  pptx_abs_path])

            print("Generating Images from pdf file")
            subprocess.run(['magick', 'convert', "-density", "300x300", os.path.abspath(os.path.join(folder, "%s.pdf" % file_name)), "-resize", sz, os.path.abspath(os.path.join(image_fdr, "%s.png" % file_name))])
    except Exception:
        logger.exception(run_i)

