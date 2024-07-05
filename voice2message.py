import openai

class VoiceToMessage:
    def __init__(self, api_key: str):
        self.transcriber = AudioTranscriber(api_key)
        self.rewriter = TranscriptRewriter(api_key)

    def process_audio(self, audio_path):
        try:
            transcript = self.transcriber.transcribe_audio(audio_path)
            if not transcript:
                raise ValueError("Transcription failed or returned empty.")
            
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
                transcript = openai.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",  # Replace with the actual Whisper model name if different
                    response_format='text'
                )
                return transcript  # Assuming 'text' field contains the transcribed text

        except FileNotFoundError:
            print(f"File '{audio_file_path}' not found.")
            return None
        
        except Exception as e:
            print(f"An error occurred during audio transcription: {e}")
            return None


class TranscriptRewriter:
    def __init__(self, api_key):
        openai.api_key = api_key
        self.prompts = {
            "chickysnail": "You must make it an extract as if I wrote this message, not voiced it. Preserve the language used in the text",
            1: "Read the following text and remove all filler words such as 'well', 'like', 'kind of' to make the text more readable. Preserve the main message and its language:",
            2: "Read the following text and highlight only the key points and important details, removing all unnecessary and repetitive phrases. Preserve original language. Ensure that the final text retains the main message and is concise and clear:",
            3: "Read the following text and structure it by adding logical pauses and paragraphs to improve readability. Preserve original language. Remove all unnecessary words and phrases, preserving the main message:",
            4: "Read the following text and edit it for business correspondence. Preserve original language. Remove filler words and unnecessary details, improving the wording to make the text look professional and neat:",
            5: "Read the following text and rewrite it to be as clear and understandable as possible. Preserve original language. Remove all filler words and unnecessary details, preserving the main message and key points:"
        }

    def rewrite_transcript(self, transcript, prompt_id=2, custom_prompt=None):
        try:
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self.prompts.get(prompt_id, self.prompts["chickysnail"])
            
            prompt_with_transcript = f"{prompt}\n\n{transcript}"

            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt_with_transcript}
                ]
            )
            
            rewritten_transcript = completion.choices[0].message
            return rewritten_transcript
        
        except Exception as e:
            print(f"An error occurred during transcript rewriting: {e}")
            return None


