from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger

log_name = 'api_routers_external_youtube'
log_dir = os.getenv("LOG_PATH", "/logs")
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

from fastapi import APIRouter, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

router = APIRouter()

# Initialize the YouTube API client with API key
youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

@router.get("/youtube-proxy")
async def youtube_proxy(videoId: str):
    try:
        # Fetch transcript using youtube-transcript-api
        transcript = YouTubeTranscriptApi.get_transcript(videoId, languages=['en'])
        transcript_lines = [{"start": entry["start"], "duration": entry["duration"], "text": entry["text"]} for entry in transcript]

        # Fetch video details using YouTube Data API
        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=videoId
        ).execute()

        if 'items' in video_response:
            video_data = video_response['items'][0]
            video_info = {
                'title': video_data['snippet']['title'],
                'author': video_data['snippet']['channelTitle'],
                'publishedAt': video_data['snippet']['publishedAt'],
                'description': video_data['snippet']['description'],
                'viewCount': video_data['statistics']['viewCount'],
                'likeCount': video_data['statistics']['likeCount'],
                'duration': video_data['contentDetails']['duration'],
            }
        else:
            video_info = {}

        return {
            "transcript": transcript_lines,
            "video_info": video_info
        }

    except HttpError as e:
        logging.error(f"An HTTP error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="YouTube API error")
    except TranscriptsDisabled:
        logging.error(f"Transcripts are disabled for video {videoId}")
        raise HTTPException(status_code=404, detail="Transcripts are disabled for this video")
    except NoTranscriptFound:
        logging.error(f"No transcript found for video {videoId}")
        raise HTTPException(status_code=404, detail="Transcript not available for this video")
    except VideoUnavailable:
        logging.error(f"Video {videoId} is unavailable")
        raise HTTPException(status_code=404, detail="Video unavailable")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
