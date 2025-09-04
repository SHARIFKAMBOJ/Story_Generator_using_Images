import os
from dotenv import load_dotenv
import google.generativeai as genai
from io import BytesIO
from PIL import Image
from gtts import gTTS
import edge_tts
import asyncio
import tempfile

# ---------------------------
# API Setup
# ---------------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("❌ API key not found in environment")

genai.configure(api_key=api_key)

# ---------------------------
# Utils
# ---------------------------
def _to_pil(img_obj):
    if isinstance(img_obj, Image.Image):
        return img_obj
    try:
        return Image.open(img_obj)
    except Exception:
        if hasattr(img_obj, "read"):
            img_obj.seek(0)
            return Image.open(img_obj)
        raise

# ---------------------------
# Image Caption Extraction
# ---------------------------
def extract_captions_from_images(images):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        pil_images = [_to_pil(im) for im in images]

        prompt = ["Describe each of these images in one very short sentence, one per line, no numbering."]
        prompt.extend(pil_images)
        response = model.generate_content(prompt)

        lines = [ln.strip(" -•\t") for ln in (response.text or "").splitlines() if ln.strip()]
        if len(lines) < len(pil_images):
            lines.extend(["(no caption)"] * (len(pil_images) - len(lines)))
        elif len(lines) > len(pil_images):
            lines = lines[:len(pil_images)]

        captions = [f"Image {i+1}: {cap}" for i, cap in enumerate(lines)]
        return captions

    except Exception as e:
        return [f"Image {i+1}: (captioning failed: {str(e)})" for i in range(len(images))]

# ---------------------------
# Prompt Creator (no tone)
# ---------------------------
def create_advanced_prompt(style, length, perspective, captions, language):
    length_map = {
        "Short": "2–3 paragraphs",
        "Medium": "4–6 paragraphs",
        "Long": "7–10 paragraphs",
    }
    length_instruction = length_map.get(length, "4–6 paragraphs")

    base_prompt = f"""
    **Persona:** You are a creative Indian storyteller.
    **Goal:** Write a {length.lower()} story in {perspective.lower()} perspective.
    **Task:** Create ONE story linking all uploaded images.
    **Style:** The story must follow the '{style}' genre.
    **Image Hints:** {', '.join(captions)}
    **Language:** Write the story in {language}.

    **Rules:**
    - Use only Indian names, places, and culture.
    - Story must have a beginning, middle, and end.
    - Length: {length_instruction}.

    **Output Format:**
    - Title at the top.
    - Then the story text.
    """

    if style == "Moral Story":
        base_prompt += "\n\n**Special Instruction:** End with `[MORAL]:` followed by the one-sentence moral."
    elif style == "Mystery":
        base_prompt += "\n\n**Special Instruction:** End with `[SOLUTION]:` revealing the culprit and clue."
    elif style == "Thriller":
        base_prompt += "\n\n**Special Instruction:** End with `[TWIST]:` revealing a shocking twist."

    return base_prompt

# ---------------------------
# Story Generation (no tone)
# ---------------------------
def generate_story_from_images(images, style, length, perspective, captions, language):
    try:
        prompt = create_advanced_prompt(style, length, perspective, captions, language)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Story generation failed: {str(e)}"

# ---------------------------
# Narration (Edge-TTS with fallback)
# ---------------------------
async def _edge_tts_full_async(text, voice):
    """Generate full TTS audio with edge-tts."""
    audio_fp = BytesIO()
    communicator = edge_tts.Communicate(text, voice=voice)
    async for chunk in communicator.stream():
        if chunk["type"] == "audio":
            audio_fp.write(chunk["data"])
        elif chunk["type"] == "end":
            break
    audio_fp.seek(0)
    return audio_fp

def narrate_story(story_text, voice_choice="Female"):
    """
    Generate narration audio for the given story text.
    Uses Edge-TTS first; falls back to gTTS if Edge fails.
    Returns BytesIO containing MP3.
    """
    voice_map = {
        "male": "en-IN-PrabhatNeural",
        "female": "en-IN-NeerjaNeural",
    }
    selected_voice = voice_map.get(str(voice_choice).strip().lower(), "en-IN-NeerjaNeural")

    try:
        # --- Edge TTS (write to temp file to avoid asyncio issues) ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
            tmp_path = tmpfile.name

        # Run Edge-TTS to save audio
        communicate = edge_tts.Communicate(text=story_text, voice=selected_voice)
        asyncio.get_event_loop().run_until_complete(communicate.save(tmp_path))

        # Load into memory for Streamlit
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.remove(tmp_path)

        return BytesIO(audio_bytes)

    except Exception as edge_err:
        print("⚠️ Edge-TTS failed, falling back to gTTS:", edge_err)

        try:
            # --- gTTS fallback ---
            fallback = BytesIO()
            tts = gTTS(text=story_text, lang="en", slow=False)
            tts.write_to_fp(fallback)
            fallback.seek(0)
            return fallback
        except Exception as gtts_err:
            print("❌ Both TTS engines failed:", gtts_err)
            return None
