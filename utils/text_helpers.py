import re

def split_message(text, max_length=4096):
    """
    Splits a long message into chunks without breaking sentences or words.
    Ensures each chunk is under max_length characters.
    """
    # First, split the text by sentence boundaries using regex.
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding the next sentence would exceed max_length, save current_chunk and start a new one
        if len(current_chunk) + len(sentence) + 1 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            # Otherwise, add the sentence to the current chunk
            current_chunk += " " + sentence

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
