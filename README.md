# video-generator
A workflow to generate videos using Amazon Polly and Translate. This script serves to complement [edx-generator](https://github.com/design-automation/edx-generator) by processing videos stored in the input folder of an unit.

The aim is:
* to shorten a video creation timeframe by employing modern text-to-speech services by [AWS Polly](https://aws.amazon.com/polly/)

* facilitate creation of educational videos from common instructional formats like powerpoint slides

* increase reach of videos by employing automated translation services

## Requirements
Listed below are essential packages used in the script

### To Download
* [unoconv](https://github.com/unoconv/unoconv)
    * Download as zip. unoconv file (without ext) required in subsequent installation steps

### Manual Installations
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
* [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
    * AWS python SDK
    * Services used: [Polly](https://aws.amazon.com/polly/), [Translate](https://aws.amazon.com/translate/), and [S3](https://aws.amazon.com/s3/)
* [moviepy](https://zulko.github.io/moviepy/)
    * version 1.0.0
    * WINDOWS USERS: provide the path to the ImageMagick binary called `magick.exe` in `PATH/TO/PYTHON/lib/site-packages/moviepy/config_defaults.py`
* [bs4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* [lxml](https://pypi.org/project/lxml/)
* [pyyaml](https://pyyaml.org/wiki/PyYAML)

## Input
### Settings
> [`__CONSTS__.py`](__CONSTS__.py)
1. Course Settings
    * Course Path should be set in a `__RUN__.bat` file. Refer to [Execute Section #6](#Execute)
    * Course path: Relative Course Path (from root folder) where units will be checked. Script iterates **3 levels deep** to get to the units from the Course Path
        ```
        `-- input
            `-- Course (Starts here)
                    |-- Section
                    |       |-- Subsection
                    |       |         `-- Unit (Target folder)
                    |       `-- Subsection
                    |                 `-- Unit (Target folder)
                    `-- Section
                            `-- Subsection
                                    `-- Unit (Target folder)
        ```
    * Expects a `__SETTINGS__.py` sibling folder
        ```
        `-- input
            |-- Course
            |
            `-- __SETTINGS__.py
        ```
        * File should include the following CONSTANTS:
            * S3_BUCKET
            * S3_MOOC_FOLDER
            * S3_VIDEOS_FOLDER
        * Videos will be uploaded onto: `S3_BUCKET\S3_MOOC_FOLDER\S3_VIDEOS_FOLDER`
1. Video settings
    * Resolution: (width, height) in px
    * Title Period: Period in which the title is shown (in seconds)
    * Font: Font to be used for video title
    * Title ideal length: length in characters. Title will be split based on specified length
    * Font size: Font size to use for title
1. Audio settings
    * Languages: Languages which will be used to generate the videos
    * Voices: Based on list available on [AWS Polly Documentation](https://docs.aws.amazon.com/polly/latest/dg/voicelist.html)
        * Take note whether neural voice is available for the voice
        * voice key is used for [AWS Translate](https://docs.aws.amazon.com/translate/latest/dg/what-is.html)
### Course Units
1. Video Settings within SRT/PPTX notes
    * Must be located in the first sequence/slide
    * Follows string JSON format:
        * video_file_name: file name for generated video
        * display_name: text for generated title
        * voice: voice to use for each language; Mapped to index of array in [`__CONSTS__.py`](__CONSTS__.py)
        ```
        {
            "video_file_name": "FILE_NAME",
            "display_name": "VIDEO TITLE",
            "voice": "1"
        }
        ```
    * `{"display_name":"break title"}` may be used to insert a title within a video
1. MP4 file with srt
    * srt sequence should start at index 1 and be appended with `_language`
    * for optimum results, ensure srt sequences are full sentences and use the start time to determine points where speech should start
        ```
        `-- input
            `-- Course
                    `-- Section
                        `-- Subsection
                                    `-- Unit
                                        |-- mp4_file_name_en.srt
                                        |-- mp4_file_name.mp4
                                        `-- mp4_file_name.yaml               
        ```
1. pptx file
    * transcripts are to be written in presenter notes
    * for optimum results, ensure presenter notes are in full sentences
        ```
        `-- input
            `-- Course
                    `-- Section
                        `-- Subsection
                                    `-- Unit
                                        |-- pptx_file_name.pptx
                                        `-- pptx_file_name.yaml
        ```
1. Accompanying language-specific srt files
    * script will use provided srt files when available
    * follows the same naming convention as shown above
    * for optimum results, ensure srt sequences are full sentences and use the start time to determine points where speech should start
    * note that translated srt files will **not** be replaced with a new translation when the core `pptx` or `mp4` file, or `_en.srt` file has been modified. Text-to-speech is based on said srt file and may not be up to date with the new modifications. To generate a new non-english srt, delete the language srt file.
        ```
        `-- input
            `-- Course
                    `-- Section
                        `-- Subsection
                                    `-- Unit
                                        |-- pptx_file_name_fr.srt <--
                                        |-- pptx_file_name_zh.srt <--
                                        |-- pptx_file_name.pptx
                                        `-- pptx_file_name.yaml
        ```

## Output
1. `videos.json` file
    * This file serves as a log to keep track of last modified time for all the pptx, mp4, and their srt files.
    * **deletion of videos.json or renaming of files will result in regeneration of the videos**
    ```
    `-- input
        `-- Course
                `-- Section
                        `-- Subsection
                                `-- Unit
                                    `-- videos.json <--
    ```
1. language specific sub files
    * The sequences are split at punctuation marks and shortened for a smoother performance
    * **They should not be reused for audio generation as the sentences will be incomplete**
    ```
    `-- input
        `-- Course
                `-- Section
                        `-- Subsection
                                `-- Unit
                                    |-- example.mp4
                                    |-- example_en.srt
                                    `-- example_sub_en.srt <--
    ```
1. translated srt files
    * The sequences are translated as-is from the original en srt file or pptx notes.
    * This file may be edited to regenerate the video of its language
    ```
    `-- input
        `-- Course
                `-- Section
                        `-- Subsection
                                `-- Unit
                                    |-- example.mp4
                                    |-- example_en.srt
                                    `-- example_zh.srt <--
    ```
## Example
[w1 > s1 > u1](input\Course\w1\s1\u1)
## Execute
1. Rename [`__AWS__.template.py`](__AWS__.template.py) to `__AWS__.py`
    * Include AWS Access Key and Secret Access Key in renamed file
1. Add to Environment Variable `LIBRE_OFFICE_PROGRAM` with value `path\to\LibreOffice\program` 
1. Copy `unoconv` (no ext) into `path\to\LibreOffice\program\`
1. Add to Environment Variable `Path` with value `path\to\ImageMagick-XXXX`
1. Add to Environment Variable `IMAGEMAGICK_BINARY` with value `path\to\ImageMagick-XXXX\magick.exe`
1. Rename [`__RUN__.template.bat`](__RUN__.template.bat) to `__RUN__.bat`
    * set path to `Course` folder
1. Execute
    ```
    .\__RUN__.bat
    ```
