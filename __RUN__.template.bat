REM Script to execute Video Generator
set script="C:/Users/patrick/Documents/Repos/edx/video-generator/vid_generator.py"
set input="C:/Users/patrick/Documents/Repos/moocs/spatial-computational-thinking-mooc/mooc1-procedural-modelling-v3"
set run_steps="2"
set folders="['w3','s3','*']"
set force="False"
python %script% %input% %run_steps% %folders% %force%