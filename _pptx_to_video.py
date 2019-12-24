import subprocess
import os
import glob
import re
import functools

from bs4 import BeautifulSoup
from _movie_to_polly import _to_time_str, VIDEO_RES
import _xml_friendly

def _pptXML_to_SRT(folder_path):
    DEFAULT_TIME_BREAK = 3 #seconds
    xml_file = glob.glob(folder_path + "*.xml")[0]

    file_name = re.sub("\.xml", "", os.path.basename(xml_file))
    slide_dict = {}
    n_slides = 0
    with open (xml_file, "rt", encoding="utf-8") as xml_f:
        soup = BeautifulSoup(xml_f, "xml")
        all_slides = soup.findAll("pkg:part", attrs={"pkg:contentType" : re.compile(r"\.notesSlide\+xml")})
        n_slides = len(all_slides)
        for slide in all_slides:
            slide_number = re.search(r"(\d+?)\.xml", slide.get("pkg:name")).group(1)
            try:
                slide_notes = re.search(r"comment. (.+)", str(slide.find("a:t", text=re.compile("comment.")))).group(1)
            except AttributeError:
                slide_notes = ""
            slide_dict[slide_number] = slide_notes
    with open(folder_path + file_name+".srt", "wt", encoding="utf-8") as srt_f:
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
            notes = notes.replace("“","\"").replace("”","\"") #.replace("’","'").replace("\u200c","")
            if notes[0]!="{":
                notes = notes.encode("ascii","ignore").decode("utf-8")
            notes = _xml_friendly.to_xml(notes)
            notes = re.sub(r"&lt;([/?sub].+?)&gt;", "<\g<1>>", notes)
            slide_dict[str(slide_i + 1)] = notes
    with open(tar_fdr + "\\" + file_name+"_en.srt", "wt", encoding="utf-8") as srt_f:
        for i in range(1, n_slides + 1):
            srt_f.write("%s\n" % str(i))
            srt_f.write("%s --> %s\n" % (_to_time_str((i-1)*DEFAULT_TIME_BREAK), _to_time_str((i)*DEFAULT_TIME_BREAK)))
            srt_f.write("%s\n" % slide_dict[str(i)])
            srt_f.write("\n")
    
def pptx_to_ingreds(pptx_path, tar_folder):
    pptx_abs_path =  os.path.abspath(pptx_path)
    folder = os.path.abspath(tar_folder)
    file_name = re.sub("\.pptx", "", os.path.basename(pptx_abs_path))
    image_fdr = os.path.abspath(os.path.join(folder, "images\\"))
    os.makedirs(image_fdr, exist_ok=True)
    sz = "%sx%s" % VIDEO_RES

    print("Converting pptx file to pdf")
    subprocess.run([os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'python.exe'), os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'unoconv'), '-f', "pdf", "-o", "%s\\%s.pdf" % (folder, file_name),  pptx_abs_path])

    print("Converting pptx file to xml")
    subprocess.run([os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'python.exe'), os.path.join(os.getenv('LIBRE_OFFICE_PROGRAM'), 'unoconv'), '-f', "xml", "-o", "%s\\%s.xml" % (folder, file_name), pptx_abs_path])

    print("Generating Images from pdf file")
    subprocess.run(['magick', 'convert', "-density", "300x300", os.path.abspath(os.path.join(folder, "%s.pdf" % file_name)), "-resize", sz, os.path.abspath(os.path.join(image_fdr, "%s.png" % file_name))])

    print("Generating SRT from xml")
    _libreXML_to_SRT(folder, os.path.dirname(pptx_path))

