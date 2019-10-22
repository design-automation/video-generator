import http.client as httplib
import httplib2

import youtube_dl

import os
import random
import time
import json
import re

from _get_by_type import *

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

httplib2.RETRIES = 1
MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

CLIENT_SECRETS_FILE = 'client_secret.json'

SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

CREDENTIALS = "auth_user_file.json"

class ToYouTubeMP4:
    def __init__(self, folder):
        self.__path = get_paths_by_typ(folder, "mp4")[0]
        self.__json = get_paths_by_typ(folder, "json")[0]
        self.__name = re.search("(.*).mp4",self.__path).group(1)

    def get_path(self):
        return self.__path
    def get_name(self):
        return self.__name
    def get_JSON(self):
        return self.__json
# This method implements an exponential backoff strategy to resume a
# failed upload.
def _resumable_upload(request): # returns video id on success
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print ('Uploading file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print ('Video id "%s" was successfully uploaded.' % response['id'])
                    return response['id']
                else:
                    exit('The upload failed with an unexpected response: %s' % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = ('A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                                    e.content))
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = 'A retriable error occurred: %s' % e

    if error is not None:
        print (error)
        retry += 1
        if retry > MAX_RETRIES:
            exit('No longer attempting to retry.')

        max_sleep = 2 ** retry
        sleep_seconds = random.random() * max_sleep
        print ('Sleeping %f seconds and then retrying...' % sleep_seconds)
        time.sleep(sleep_seconds)

def _initialize_upload(youtube, options):
    body=dict(
        snippet=dict(
            title=options["title"],
            description=options["description"],
            tags=options["tags"]
        ),
        status=dict(
            privacyStatus=options["privacyStatus"]
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
    part=','.join(body.keys()),
    body=body,
    # entire file uploaded in single http request
    media_body = MediaFileUpload(options["file"], chunksize=-1, resumable=True)
    )

    resp_id = _resumable_upload(insert_request)
    return resp_id

def _get_yt_vid(yt_service, id):
    videos_response = yt_service.videos().list(
        id=id,
        part="snippet"
    ).execute()
    if not videos_response["items"]:
        raise Exception("'%s' was not found. " % id)
    else:
        return videos_response["items"][0]

def _get_caption_lst(yt_service, id):
    caption_resp = yt_service.captions().list(part="snippet", videoId=id).execute()
    caption_lst = caption_resp["items"]
    return caption_lst

def _filterNotASR(caption_dict):
    return caption_dict["snippet"]["trackKind"] != "ASR"

def _filterASR(caption_dict):
    return caption_dict["snippet"]["trackKind"] == "ASR"
        
def get_authenticated_service(): # creates youtube service object
    credentials = None
    if os.path.isfile(CREDENTIALS):
        # use access/refresh token
        print("Using Saved Token")
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(CREDENTIALS)
    else:
        # request for authorisation
        print("Requesting New Token")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_console()
    # update cred json
    creds_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    with open(CREDENTIALS, 'w', encoding='utf-8') as f:
        json.dump(creds_data, f, ensure_ascii=False, indent=4)
    return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

def upload_vid(yt_service, vid_path, yt_details): # returns video id on success
    args = yt_details # includes title, descriptions, tags
    args["file"] = vid_path
    args["privacyStatus"] = "unlisted"

    resp_id = None
    try:
        resp_id = _initialize_upload(yt_service, args)
    except HttpError as e:
        raise HttpError ('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))
    if resp_id!= None:
        return resp_id

def update_vid_details(yt_service, id, yt_details):
    yt_snippet = _get_yt_vid(yt_service, id)["snippet"]
    for detail in yt_details:
        yt_snippet[detail] = yt_details[detail]
    try:
        videos_update_response = yt_service.videos().update(
            part="snippet",
            body=dict(
                snippet=yt_snippet,
                id=id
            )).execute()
        print(id + " Details Updated.")
    except HttpError as e:
        raise HttpError ('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))

def dl_captions(yt_service, id, folder, ASR):
    caption_lst = _get_caption_lst(yt_service,id)#[0]["id"]
    caption_id = ""
    if ASR:
        caption_id = list(filter(_filterASR, caption_lst))[0]["id"]
    else:
        caption_id = list(filter(_filterNotASR,caption_lst))[0]["id"]
    caption_bin = yt_service.captions().download(id=caption_id, tfmt="srt").execute()
    with open("%s%s_captions.srt" % (folder,id), "wt", encoding="utf-8") as srt_f:
        srt_f.write(caption_bin.decode("utf-8"))

def del_vid(yt_service, id):
    try:
        delete_request = yt_service.videos().delete(id=id).execute()
        print(id + " Deleted.")
    except HttpError as e:
        raise HttpError ('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))

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
