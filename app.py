import streamlit as st 
import streamlit_sortables as sortables
from story_generator import (
    generate_story_from_images,
    extract_captions_from_images,
    narrate_story,
)

st.set_page_config(page_title="AI Story Generator", layout="wide")

st.title("📖 AI Story Generator from Images")
st.write("Upload images, pick a style, and watch your story come alive ✨")

# ----------------------------
# SIDEBAR OPTIONS
# ----------------------------
st.sidebar.header("⚙️ Story Settings")

story_styles = st.sidebar.selectbox(
    "Choose a story style",
    (
        "Comedy",
        "Thriller",
        "Fairy Tale",
        "Sci-Fi",
        "Mystery",
        "Adventure",
        "Moral Story",
        "Romance",
        "Horror",
        "Mythology",
        "Motivational",
    ),
)

length = st.sidebar.radio("Story Length", ["Short", "Medium", "Long"])
perspective = st.sidebar.radio("Perspective", ["First Person", "Third Person"])

language = st.sidebar.selectbox(
    "Story Language", ["English", "Hindi", "Spanish", "French"]
)

# Narration option
narrate = st.sidebar.checkbox("🎧 Add narration (Text-to-Speech)", value=True)

voice_choice = None
if narrate:
    voice_choice = st.sidebar.radio("Choose Narration Voice", ["Male", "Female"], index=1)

# Dynamic button & spinner text
button_text = "✨ Generate Story + Narration" if narrate else "✨ Generate Story"
spinner_text = (
    "📝 The AI is writing and narrating your story..... This may take a few moments."
    if narrate
    else "📝 The AI is writing your story..... This may take a few moments."
)

# ----------------------------
# SESSION STATE
# ----------------------------
if "captions" not in st.session_state:
    st.session_state.captions = None
if "story_text" not in st.session_state:
    st.session_state.story_text = None
if "audio_fp" not in st.session_state:
    st.session_state.audio_fp = None

# ----------------------------
# IMAGE UPLOAD
# ----------------------------
uploaded_images = st.file_uploader(
    "📂 Select one or more pictures (max 10) to begin:",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

image_order = []
if uploaded_images:
    st.write("🖼️ Drag & drop to reorder images:")
    image_order = sortables.sort_items(
        [img.name for img in uploaded_images],
        direction="horizontal",
        key="sortable_images",
    )

    # Apply the reordering to uploaded_images
    uploaded_images = sorted(uploaded_images, key=lambda x: image_order.index(x.name))

    # ----------------------------
    # IMAGE PREVIEW (synced with order)
    # ----------------------------
    st.subheader("👀 Preview Uploaded Images")
    cols = st.columns(min(len(uploaded_images), 4))  # Show 4 per row

    for i, img in enumerate(uploaded_images):
        with cols[i % 4]:
            st.image(
                img,
                caption=f"Image {i+1}: {img.name}",
                use_container_width=True,
            )

# ----------------------------
# GENERATE STORY
# ----------------------------
if uploaded_images and st.button(button_text, type="primary"):
    if narrate:
        with st.spinner(spinner_text):
            st.session_state.captions = extract_captions_from_images(uploaded_images)
            st.session_state.story_text = generate_story_from_images(
                uploaded_images,
                story_styles,
                length,
                perspective,
                st.session_state.captions,
                language,
            )
            st.session_state.audio_fp = narrate_story(
                st.session_state.story_text, voice_choice
            )
    else:
        with st.spinner(spinner_text):
            st.session_state.captions = extract_captions_from_images(uploaded_images)
            st.session_state.story_text = generate_story_from_images(
                uploaded_images,
                story_styles,
                length,
                perspective,
                st.session_state.captions,
                language,
            )
            st.session_state.audio_fp = None

# ----------------------------
# REGENERATE STORY (no re-upload)
# ----------------------------
if st.session_state.captions and st.button("🔄 Regenerate Story"):
    with st.spinner("✨ Creating a new version of your story..."):
        st.session_state.story_text = generate_story_from_images(
            uploaded_images,
            story_styles,
            length,
            perspective,
            st.session_state.captions,
            language,
        )
        if narrate:
            st.session_state.audio_fp = narrate_story(
                st.session_state.story_text, voice_choice
            )
        else:
            st.session_state.audio_fp = None

# ----------------------------
# SHOW RESULTS
# ----------------------------
if st.session_state.story_text:
    st.markdown(
        f"""
        <div style="padding:20px; background-color:#fdf6e3; border-radius:12px;
                    font-family:Georgia; font-size:18px; line-height:1.6;">
            <h2 style="color:#b22222;">📖 Your Story</h2>
            {st.session_state.story_text.replace("\n", "<br>")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Narration (if available)
    if st.session_state.audio_fp:
        st.audio(st.session_state.audio_fp, format="audio/mp3")
        st.download_button(
            "🎧 Download Narration",
            st.session_state.audio_fp,
            "story.mp3",
            mime="audio/mpeg",
        )

    # Always allow text download
    st.download_button(
        "📄 Download Story", st.session_state.story_text, "story.txt"
    )
