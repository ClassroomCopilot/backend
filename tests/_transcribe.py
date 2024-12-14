from modules.whisper_live.client import TranscriptionClient
import os
import time

def setup_directories(user_dir, user_id):
    user_transcript_dir = f"{user_dir}/{user_id}/transcripts"
    if not os.path.exists(user_transcript_dir):
        os.makedirs(user_transcript_dir)
    return user_transcript_dir

def timestamped_callback(text, is_final):
    if is_final:
        print(f"Timestamp: {time.strftime('%H:%M:%S')}, Transcription: {text}")

def main():
    user_dir = "../../data/users"
    user_id = "kcar"
    user_transcript_dir = setup_directories(user_dir, user_id)

    client = TranscriptionClient(
        "localhost",
        9090,
        lang="en",
        translate=False,
        use_vad=True,
        save_output_recording=True,
        output_recording_filename=f"{user_transcript_dir}/output_recording.wav",
        output_transcription_path=f"{user_transcript_dir}/output.srt",
    )

    client()

if __name__ == "__main__":
    main()
