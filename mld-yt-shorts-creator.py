#!/usr/bin/python

#works with https://docs.google.com/spreadsheets/d/1JkqN2h_e33PHsJ8bMqvOxT9GdHiSGsJxdUHjulM1xSE/edit#gid=0

import os
import random
import sys
import time
import csv
import datetime

from oauth2client.tools import argparser

SIMULATION = False

def process_index_tsv_file(options):
  text_display_time=int(options.text_time)
  output_video_duration=int(options.video_duration)													

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
      background_footage = row["background_footage"]
      

      if not skip == "1":
        #ToDo: Check if the ffmpeg execution went well and if not leave a trace in a log file
        now = datetime.datetime.now()
        print(f"{now} Processing {video_title} with filename {output_filename}" )



        ffmpeg_command = "ffmpeg -hide_banner -nostats -loglevel error -y "
        ffmpeg_command += "-i {} ".format("audioSpectrum.mp4")
        #ffmpeg_command += "-i {} ".format(options.background_image)
        ffmpeg_command += "-i {} ".format(background_footage)
        ffmpeg_command += "-i {} ".format("initLogo640.png")
        ffmpeg_command += "-i {} ".format("subscribe.mp4")
        ffmpeg_command += "-ss {} -i {} ".format(start_time, options.session_file)
        ffmpeg_command += "-filter_complex \""
        ffmpeg_command += "[0:v] colorkey=0x00C800:0.1:0.5,transpose=2, colorchannelmixer=aa=0.4 [ckey]; " #Remove green background to audioSpectrum video
        ffmpeg_command += "[3:v] colorkey=0x6de200:0.1:0.5 [ckeySubscribe]; "
        ffmpeg_command += "[ckeySubscribe] setpts=PTS-STARTPTS+5/TB [subscribe]; "
        ffmpeg_command += "[1:v] loop=loop=3:size=32000:start=1 [fondo]; " #Changes to background footage, currently a null filter to preserve it with no changes or scaling to 720x1280
        ffmpeg_command += "[fondo] scale=720:1280 [fondoEscalado]; "
        ffmpeg_command += "[fondoEscalado][ckey] overlay=25:0 [fondo_y_spectrum]; "
        ffmpeg_command += "[fondo_y_spectrum][subscribe] overlay=0:0:enable=between(t\,5\,9) [fondoSpectrumSubscribe]; "
        ffmpeg_command += "[fondoSpectrumSubscribe][2:v] overlay=40:40 [fondoEspectroYLogo]; "
        ffmpeg_command += "[fondoEspectroYLogo] drawbox=x=0:y=880:w=720:h=190:color=0x8a00c2@0.5:thickness=fill:enable=between(t\,0\,{}), ".format(text_display_time)
        ffmpeg_command += "drawtext=fontfile=font.otf:text='{}':x=(w-text_w)/2:y=900:fontsize=48:fontcolor=white:box=0:enable=between(t\,0\,{}), ".format(top_track_title, text_display_time)
        ffmpeg_command += "drawtext=fontfile=font.otf:text='{}':x=(w-text_w)/2:y=980:fontsize=48:fontcolor=white:box=0:enable=between(t\,0\,{})[fondoEspectroLogoYTexto]; ".format(bottom_track_title, text_display_time)
        ffmpeg_command += "color=white@0.5:s=720x20[progressBar]; [fondoEspectroLogoYTexto][progressBar] overlay='if(lte(t,{}),-720+{}*t,-720)':1050 [output]".format(text_display_time, 720/text_display_time)
        ffmpeg_command += "\" "
        ffmpeg_command += "-t {} ".format(output_video_duration) 
        ffmpeg_command += "-c:v libx264 -preset medium -tune stillimage -crf 18 -c:a aac -b:a 192k -pix_fmt yuv420p "
        ffmpeg_command += "-map \"[output]\" -map 4:a \"{}\".mkv".format(output_filename)

        ffmpeg_thumbnail_command = "ffmpeg -hide_banner -nostats -loglevel error -y "
        ffmpeg_thumbnail_command += "-ss 00:00:{} -i \"{}\".mkv -frames:v 1 -q:v 2 \"{}\".jpg".format(output_video_duration-1, output_filename, output_filename)

        if not SIMULATION:
          os.system(ffmpeg_command)
          os.system(ffmpeg_thumbnail_command)
        else:
           print(ffmpeg_command)
        print("")



if __name__ == '__main__':
  argparser.add_argument("--index_file", required=True, help="TSV file with the index of the videos to generate")
  #argparser.add_argument("--background_image", required=True, help="720x1280 image to use as still frame for the video", default="imagen720.png")
  argparser.add_argument("--session_file", required=True, help="MP3 file with the session corresponding to the index_file")
  argparser.add_argument("--text_time", required=False, help="Time to show the tracks titles and progress bar", default=32)
  argparser.add_argument("--video_duration", required=False, help="Length of the created short video", default=32)

  args = argparser.parse_args()
  process_index_tsv_file(args)