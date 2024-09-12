import os
import logging
from moviepy.editor import VideoFileClip

def convert_video_to_audio(video_path):
    # Create the output directory if it doesn't exist
    output_dir = 'audios'
    os.makedirs(output_dir, exist_ok=True)

    # Extract the filename and extension from the video path
    video_filename = os.path.basename(video_path)
    audio_filename = os.path.splitext(video_filename)[0] + '.mp3'

    # Set the output audio path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    audio_path = os.path.join(current_dir, output_dir, audio_filename)

    # Convert the video to audio
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    
    # Release the resources held by VideoFileClip
    video.close()
    
    # Delete the initial video file
    os.remove(video_path)
    logging.info(f"Deleted video file: {video_path}; Converted to audio: {audio_path}")
    
    # Return the path of the converted audio file
    return audio_path

if __name__ == "__main__":
    video_path = 'user_files/test.mp4'
    audio_path = convert_video_to_audio(video_path)
    print(f"Audio file saved at: {audio_path}")