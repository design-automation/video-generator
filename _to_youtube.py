import youtube_dl

def dl_vid(yt_id, folder, vid_id, vid_name): # this does not use the official youtube api as YouTube does not allow downloading of videos
    ydl_opts = {
        'outtmpl': folder + "%s_%s" % (vid_id, vid_name) + ".%(ext)s",
        'format': 'best', #22
        'writesubtitles': folder + "%s_%s" % (vid_id, vid_name) + ".%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'srt',
        }]
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/watch?v=' + yt_id])
