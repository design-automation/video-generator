from bs4 import BeautifulSoup
import glob
import re
from _movie_to_polly import _to_time_str

FOLDER = "PPT_XML\\"
DEFAULT_TIME_BREAK = 5 #seconds
xml_files = glob.glob(FOLDER + "*.xml")

for xml_file in xml_files:
    file_name = re.search(r"\\(.+?)\.xml", xml_file).group(1)
    slide_dict = {}
    n_slides = 0
    with open (xml_file, "rt", encoding="utf-8") as xml_f:
        soup = BeautifulSoup(xml_f, "xml")
        all_slides = soup.findAll("pkg:part", attrs={"pkg:contentType" : re.compile(r"\.notesSlide\+xml")})
        n_slides = len(all_slides)
        for slide in all_slides:
            slide_number = re.search(r"(\d+?)\.xml", slide.get("pkg:name")).group(1)
            slide_notes = re.search(r"comment. (.+)", str(slide.find("a:t", text=re.compile("comment.")))).group(1)
            slide_dict[slide_number] = slide_notes
    with open(FOLDER + file_name+".srt", "wt", encoding="utf-8") as srt_f:
        for i in range(1, n_slides + 1):
            srt_f.write("%s\n" % str(i))
            srt_f.write("%s --> %s\n" % (_to_time_str((i-1)*DEFAULT_TIME_BREAK), _to_time_str((i)*DEFAULT_TIME_BREAK)))
            srt_f.write("%s\n" % slide_dict[str(i)])
            srt_f.write("\n")