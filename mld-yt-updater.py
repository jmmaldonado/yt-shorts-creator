ToDo = '''

  [X] Actualizar el titulo y la descripcion del video
  [X] Anadir el video actualizdo a la playlist de shorts
  [] Sacar el video procesado de la playlist ToBeProcessed
  [] Eliminar el fichero local del video subido a mano ?
  [] Buscar los hashtags mas relevantes para ponerlos en la descripcion?
  [X] Configurar el thumbnail generado por ffmpeg

'''

# works with https://docs.google.com/spreadsheets/d/1JkqN2h_e33PHsJ8bMqvOxT9GdHiSGsJxdUHjulM1xSE/edit#gid=0


import http.client as httplib
import httplib2
import os
import random
import sys
import time
import csv
import ffmpeg

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

SIMULATION = False

#This program consumes the index TSV file with the details of the videos
#Gets the list of all the uploaded videos, and updates the title, details, keywords, etc...
#for all of those that have been uploaded manually
#It is to prevent the quota exhaustion that comes from uploading videos via API

YOUTUBE_CHANNEL_ID = "UC9i1ZzYfxSqFTCyMkDunKLw"
YOUTUBE_TOBEPROCESSED_PLAYLIST = "PLmo-ARio7-J1G_Hx_K8oS_3KB1jjRU42i"
YOUTUBE_SHORTS_PLAYLIST = "PLmo-ARio7-J1S8P-sHz3ZqxSGs8UXtwdR"

CLIENT_SECRETS_FILE = "creds.json"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = "Missing creds.json file, get one from the API credentials google console"


def get_authenticated_service(args):
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    scope=YOUTUBE_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))



def get_videos_to_be_processed(youtube):
  # Dictionary with key = youtube video title and value = youtube videoId
  video_list = {}

  # Retrieve the list of videos uploaded to the authenticated user's channel.
  playlistitems_list_request = youtube.playlistItems().list(
    playlistId=YOUTUBE_TOBEPROCESSED_PLAYLIST,
    part="snippet",
    maxResults=50
  )

  while playlistitems_list_request:
    playlistitems_list_response = playlistitems_list_request.execute()

    # Print information about each video.
    for playlist_item in playlistitems_list_response["items"]:
      title = playlist_item["snippet"]["title"]
      video_id = playlist_item["snippet"]["resourceId"]["videoId"]
      video_list[title] = video_id

    playlistitems_list_request = youtube.playlistItems().list_next(
      playlistitems_list_request, playlistitems_list_response
    )

  return video_list


def get_details_from_index_file(options):
  video_details_dict = {}											

  with open(options.index_file, "r", encoding="utf8") as session_file:
    tsv_reader = csv.DictReader(session_file, delimiter="\t")
    
    for row in tsv_reader:
      skip = row["skip"]
      start_time = row["start_time"]
      top_track_artist = row["top_track_artist"]
      top_track_title = row["top_track_title"]
      bottom_track_title = row["bottom_track_title"]
      bottom_track_artist = row["bottom_track_artist"]
      output_filename = row["output_filename"]
      video_title = row["video_title"]
      video_description = row["video_description"]
      publish_datetime = row["publish_datetime"]

      if not skip == "1":
        video_details = {
          "title": video_title,
          "description": video_description.replace( '\\n', '\n' ),
          "categoryId": 10,
          "publish_datetime": publish_datetime,
          "output_filename": output_filename
        }
        video_details_dict[output_filename.replace("_", " ")] = video_details
    
  return video_details_dict


def process_videos_and_details(youtube, videos, details):
  not_processed_videos = {}
  for uploaded_video_title in videos:
    if uploaded_video_title in details:
      detail = details[uploaded_video_title]
      detail["video_id"] = videos[uploaded_video_title]
      print(f"Updating video {detail['video_id']} with original title: {detail['output_filename']} ")
      update_video(youtube, detail)
    else:
      print(f"Video {uploaded_video_title} not present in details")
  



def update_video(youtube, video_detail):

  #update the video thumbnail
  videos_thumbnail_response = youtube.thumbnails().set(
    videoId=video_detail["video_id"],
    media_body="{}.jpg".format(video_detail["output_filename"])
  ).execute()


  # Update the video resource by calling the videos.update() method.
  videos_update_response = youtube.videos().update(
    part="snippet,status",
    body=dict(
      id=video_detail["video_id"],
      snippet=video_detail,
      status=dict(
        privacyStatus="private",
        publishAt=video_detail["publish_datetime"]
      )
    )
  ).execute()


  #Add the video to the shorts playlist
  playlist_update_response = youtube.playlistItems().insert(
    part="snippet",
    body=dict(
      snippet=dict(
        playlistId=YOUTUBE_SHORTS_PLAYLIST,
        resourceId=dict(
          kind="youtube#video",
          videoId=video_detail["video_id"]
        )
      )
    )
  ).execute()


if __name__ == '__main__':
  argparser.add_argument("--index_file", required=True, help="TSV file with the index of the videos to update")
  args = argparser.parse_args()

  youtube = get_authenticated_service(args)
  yt_video_list = get_videos_to_be_processed(youtube)
  video_details_dict = get_details_from_index_file(args)

  process_videos_and_details(youtube, yt_video_list, video_details_dict) if not SIMULATION else print(video_details_dict)

  print("All done, dont forget to remove the videos from the ToBeProcessed playlist in YouTube")


