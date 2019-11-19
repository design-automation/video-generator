# video-generator
A workflow to generate videos using Amazon Polly and Translate. This script serves to complement [edx-generator](https://github.com/design-automation/edx-generator) by processing videos stored in the input folder of an unit.

The aim is:
* to shorten a video creation timeframe by employing modern text-to-speech services by [AWS Polly](https://aws.amazon.com/polly/)

* facilitate creation of educational videos from common instructional formats like powerpoint slides

* increase reach of videos by employing automated translation services

## Requirements
Listed below are essential packages used in the script

### Manual Installations
* [Image Magick](https://www.imagemagick.org/script/index.php)
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
* [youtube_dl](https://pypi.org/project/youtube_dl/)
* [unoconv](https://github.com/unoconv/unoconv)
* [bs4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* [lxml](https://pypi.org/project/lxml/)

## Input
### Settings
> [`__CONSTS__.py`](__CONSTS__.py)
1. Correct Path to IMAGEMAGICK exe is required for script to work
1. Relative Course Path (from root folder) where units will be checked. Script iterates **3 levels deep** to get to the units from the Course Path
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
1. Video settings
    * Resolution: (width, height) in px
    * Title Period: Period in which the title is shown (in seconds)
1. Audio settings
    * Languages: Languages which will be used to generate the videos
    * Voices: Based on list available on [AWS Polly Documentation](https://docs.aws.amazon.com/polly/latest/dg/voicelist.html)
        * Take note whether neural voice is available for the voice
        * voice key is used for [AWS Translate](https://docs.aws.amazon.com/translate/latest/dg/what-is.html)
### Course Units
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
                                        `-- mp4_file_name.md               
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
                                        `-- pptx_file_name.md
        ```
1. Accompanying language-specific srt files
    * script will use provided srt files when available
    * follows the same naming convention as shown above
    * for optimum results, ensure srt sequences are full sentences and use the start time to determine points where speech should start
    * note that translated srt files that will be replaced if the core `pptx` or `mp4` file, or `_en.srt` file has been modified
        ```
        `-- input
            `-- Course
                    `-- Section
                        `-- Subsection
                                    `-- Unit
                                        |-- pptx_file_name_fr.srt <--
                                        |-- pptx_file_name_zh.srt <--
                                        |-- pptx_file_name.pptx
                                        `-- pptx_file_name.md
        ```

## Output
1. `videos.json` file
    * This file serves as a log to keep track of last modified time for all the pptx, mp4, and their md and srt files.
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
[Section 1> Subsection 2 > Unit 1](input/Course/Section_Week_1/Subsection_2_Shorts/Unit_1_Text_Imgs_and_Videos)
## Execute
1. Rename [`__AWS__.template.py`](__AWS__.template.py) to `__AWS__.py`
    * Include AWS Access Key, Secret Access Key, and S3 Bucket name in renamed file
1. Set Path to MAGICK.exe file in [`__CONSTS__.py`](__CONSTS__.py)
1. Execute
    ```
    python vid_generator.py
    ```
