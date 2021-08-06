# Running the Video Generator

Listed below are software tools and packages used in the script.

### To Download

Download the following:

* [unoconv](https://github.com/unoconv/unoconv)
    * Download as zip. unoconv file (without ext) required in subsequent installation steps

### Manual Installations

Install the following:

* [Image Magick](https://www.imagemagick.org/script/index.php)
    * [7.0.9-5-Q16 (breaks with latest: Q8)](INSTALL\ImageMagick-7.0.9-5-Q16-x64-dll.exe)
    * used by moviepy in the video creation process
    * conversion of .pdf to .png
* [Libre Office](https://www.libreoffice.org/)
    * used by unoconv to convert pptx to pdf
    * used by unoconv to convert pptx to xml
* [GhostScript](https://www.ghostscript.com/)
    * required by unoconv to facilitate conversion to pdf

### pip packages

This Python3 script requires four python modules. These can be installed with `pip` as follows:

* `pip install boto3`
* `pip install moviepy`
* `pip install bs4`
* `pip install lxml`

For more information:

* [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
    * AWS python SDK
    * Services used: [Polly](https://aws.amazon.com/polly/), [Translate](https://aws.amazon.com/translate/), and [S3](https://aws.amazon.com/s3/)
* [moviepy](https://zulko.github.io/moviepy/)
    * version 1.0.0
    * WINDOWS USERS: provide the path to the ImageMagick binary called `magick.exe` in `PATH/TO/PYTHON/lib/site-packages/moviepy/config_defaults.py`
* [bs4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* [lxml](https://pypi.org/project/lxml/)


## Setup

1. Rename [`__AWS__.template.py`](__AWS__.template.py) to `__AWS__.py`
    * Include AWS Access Key and Secret Access Key in renamed file
1. Add to Environment Variable `LIBRE_OFFICE_PROGRAM` with value `path\to\LibreOffice\program` 
1. Copy `unoconv` (no ext) into `path\to\LibreOffice\program\`
1. Add to Environment Variable `Path` with value `path\to\ImageMagick-XXXX`
1. Add to Environment Variable `IMAGEMAGICK_BINARY` with value `path\to\ImageMagick-XXXX\magick.exe`
1. Restart your computer.

## Execute

Execute the video generator:
```
python path_to_vid_generator.py path_to_MOOC_root_folder run_steps folders force(optional)
```
The arguments are as follows:
* _path_to_MOOC_root_folder_: 
* _run_steps_: Can be `0`, `1`, or `2`:
  * `run_steps = 0`: Generate data files for the video generation (such as mp3 audio files and other types of files). These files will all be saved in a sub-folders inside the folder where the `.pptx` files are located. 
  * `run_steps = 1`: Generate mp4 video files from the data files generated in the previous step. The data folder and files will all be deleted after the video is generated.
  * `run_steps = 2`: Run both steps above.
* _folders_: The folders to search, for example `['w1','s2','u3']` would generate videos for week 1, section 2, unit 3. And level can be replaced by `*`. For example `['*','*','*']` would generate all the videos for the whole MOOC.
* _force_: If set to `True`, it will force all videos to be regenerated. If set to `False` will only regenerate videos if changes are detected. The default is `False`.

For example:
```
python "C:/xxxx/vid_generator.py" "C:/yyyy/mooc1-procedural-modelling" "0" "['w1','s2','u3']" "False"
```

