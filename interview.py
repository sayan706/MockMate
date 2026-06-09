import os
import sys
import re
import json
import time
import pyttsx3
from dotenv import load_dotenv
from openai import OpenAI

# ==================================
# LOAD ENV
# ==================================

load_dotenv()

# ==================================
# CONFIG
# ==================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise Exception(
        "Please set DEEPSEEK_API_KEY in your .env file."
    )

MODEL = "deepseek-chat"   # DeepSeek-V3 — best model
MAX_QUESTIONS = 10

# ==================================
# DEEPSEEK CLIENT (OpenAI-compatible)
# ==================================

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================================
# STRIP MARKDOWN FOR TTS
# ==================================

def strip_markdown(text):
    """Remove markdown formatting so TTS reads
    clean, natural-sounding text."""

    # Remove code blocks (``` ... ```)
    text = re.sub(r"```[\s\S]*?```", "", text)

    # Remove inline code (`...`)
    text = re.sub(r"`([^`]*)`", r"\1", text)

    # Remove bold + italic (***text***)
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)

    # Remove bold (**text**)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)

    # Remove italic (*text*)
    text = re.sub(r"\*(.+?)\*", r"\1", text)

    # Remove headings (### text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove blockquotes (> text)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***, ___)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove unordered list markers (- or * at line start)
    text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)

    # Remove ordered list markers (1. 2. etc.)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)

    # Remove image/link markdown ![alt](url) and [text](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ==================================
# TEXT TO SPEECH
# ==================================

def speak(text):
    """Print and speak the AI's response."""

    print("\n" + "=" * 80)
    print("🤖 INTERVIEWER:")
    print(text)
    print("=" * 80 + "\n")

    # Strip markdown so TTS doesn't read
    # symbols like *, #, >, ` aloud
    clean_text = strip_markdown(text)

    # Reinitialize engine every call to avoid
    # the Windows pyttsx3 freeze bug
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.say(clean_text)
    engine.runAndWait()
    engine.stop()


# ==================================
# USER INPUT (TYPED)
# ==================================

def get_user_input():
    """Get typed input from the user."""

    print("─" * 40)
    answer = input("✍️  YOUR ANSWER: ")
    print("─" * 40)

    return answer.strip()


# ==================================
# DEEPSEEK RETRY LOGIC
# ==================================

def generate_with_retry(messages, retries=5):

    for attempt in range(retries):

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )

            return response.choices[0].message.content

        except Exception as e:

            print(
                f"\nDeepSeek Error "
                f"(Attempt {attempt + 1}/{retries})"
            )

            print(str(e))

            if attempt == retries - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"Retrying in "
                f"{wait_time} seconds..."
            )

            time.sleep(wait_time)


# ==================================
# LOAD INTERVIEW PROFILES
# ==================================

def load_interviews():
    """Load interview profiles from JSON."""

    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "interviews.json"
    )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data["interviews"]


# ==================================
# DISPLAY MENU
# ==================================

def display_menu(interviews):
    """Show interview selection menu."""

    print("\n" + "═" * 60)
    print("   🎯  AI INTERVIEW COACH  🎯")
    print("═" * 60)
    print()
    print("   Choose your interview type:\n")

    for item in interviews:
        print(
            f"   {item['id']}. {item['emoji']}  "
            f"{item['name']}"
        )
        print(
            f"      └─ {item['description']}"
        )
        print()

    print("═" * 60)


# ==================================
# GET USER CHOICE
# ==================================

def get_choice(interviews):
    """Get valid interview selection from user."""

    valid_ids = [item["id"] for item in interviews]

    while True:

        try:
            choice = int(
                input("\n👉 Enter your choice (1-4): ")
            )

            if choice in valid_ids:
                return choice

            print("❌ Invalid choice. Try again.")

        except ValueError:
            print("❌ Please enter a number.")


# ==================================
# RUN INTERVIEW
# ==================================

def run_interview():
    """Main interview flow."""

    # Load profiles
    interviews = load_interviews()

    # Show menu
    display_menu(interviews)

    # Get selection
    choice = get_choice(interviews)

    # Find selected interview
    selected = next(
        item for item in interviews
        if item["id"] == choice
    )

    print(
        f"\n✅ Selected: "
        f"{selected['emoji']} {selected['name']}"
    )
    print("─" * 60)
    print(
        "📋 You will be asked up to "
        f"{MAX_QUESTIONS} questions."
    )
    print(
        "📝 Type your answers when prompted."
    )
    print(
        "🔊 The interviewer will speak "
        "each question aloud."
    )
    print("─" * 60)

    input("\n⏎  Press ENTER to start the interview...")

    # ==================================
    # BUILD MESSAGES (OpenAI format)
    # ==================================

    system_prompt = selected["system_prompt"]

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": "Please begin the interview."
        }
    ]

    # ==================================
    # FIRST QUESTION
    # ==================================

    print(
        f"\n🚀 Starting {selected['name']} "
        f"Mock Interview\n"
    )

    first_question = generate_with_retry(messages)

    messages.append({
        "role": "assistant",
        "content": first_question
    })

    speak(first_question)

    # ==================================
    # INTERVIEW LOOP
    # ==================================

    for question_number in range(MAX_QUESTIONS):

        answer = get_user_input()

        # Allow early exit
        if answer.lower() in ("quit", "exit", "stop"):
            print("\n⏹️  Ending interview early...")
            break

        messages.append({
            "role": "user",
            "content": answer
        })

        next_question = generate_with_retry(messages)

        messages.append({
            "role": "assistant",
            "content": next_question
        })

        speak(next_question)

    # ==================================
    # FINAL REPORT
    # ==================================

    messages.append({
        "role": "user",
        "content": """
INTERVIEW_FINISHED

Generate detailed evaluation report.

Include all scoring criteria and
provide a comprehensive assessment
with improvement plan and final remarks.
"""
    })

    print("\n⏳ Generating final report...\n")

    report = generate_with_retry(messages)

    print("\n" + "═" * 80)
    print(
        f"📊 FINAL REPORT — "
        f"{selected['name']}"
    )
    print("═" * 80)
    print(report)
    print("═" * 80)
    print(
        "\n🎉 Interview session complete! "
        "Good luck with your preparation!\n"
    )


# ==================================
# ENTRY POINT
# ==================================

if __name__ == "__main__":
    run_interview()