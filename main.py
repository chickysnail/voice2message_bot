import sys
from voice2message import VoiceToMessage
import configparser

def main(config_file, audio_path):
    # Load API key from config file
    config = configparser.ConfigParser()
    config.read(config_file)
    api_key = config['credentials']['api_key']

    # Example usage: process_audio with the specified audio file path
    voice_to_message = VoiceToMessage(api_key)
    rewritten_transcript = voice_to_message.process_audio(audio_path)
    if rewritten_transcript:
        print(rewritten_transcript)
    else:
        print("Failed to process audio and rewrite transcript.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <config_file> <audio_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    audio_path = sys.argv[2]
    main(config_file, audio_path)
