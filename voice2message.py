import openai

class VoiceToMessage:
    def __init__(self, api_key: str):
        self.transcriber = AudioTranscriber(api_key)
        self.rewriter = TranscriptRewriter(api_key)

    def process_audio(self, audio_path, is_summary=True):
        try:
            transcript = self.transcriber.transcribe_audio(audio_path)
            if not transcript:
                raise ValueError("Transcription failed or returned empty.")
            
            if not is_summary:
                return transcript
            
            rewritten_transcript = self.rewriter.rewrite_transcript(transcript)
            return rewritten_transcript
        
        except Exception as e:
            print(f"An error occurred during audio processing: {e}")
            return None


class AudioTranscriber:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = self.api_key

    def transcribe_audio(self, audio_file_path: str):
        try:
            with open(audio_file_path, 'rb') as audio_file:
                response  = openai.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",  # Replace with the actual Whisper model name if different
                    response_format='json'
                )
                transcript = response.text
                return transcript

        except FileNotFoundError:
            print(f"File '{audio_file_path}' not found.")
            return None
        
        except Exception as e:
            print(f"An error occurred during audio transcription: {e}")
            return None


class TranscriptRewriter:
    def __init__(self, api_key):
        openai.api_key = api_key
        self.default_prompt = "Rewrite the following transcript as if it were a text message. Make the text more readable. Keep the main point of the message. The message will be read by the user. The user only speaks the language they recorded the audio in. Preserve user's language"

    def rewrite_transcript(self, transcript, custom_prompt=None):
        try:
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self.default_prompt
            
            completion = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": transcript}
                ]
            )
            
            rewritten_transcript = completion.choices[0].message
            return rewritten_transcript.content
        
        except Exception as e:
            print(f"An error occurred during transcript rewriting: {e}")
            return None


