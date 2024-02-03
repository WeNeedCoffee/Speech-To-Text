#!/usr/bin/env python3
import threading
import pyautogui
import speech_recognition
import winsound
import openai
import clipboard
import os
import time

lock_file = "lock_file.lock"

if os.path.exists(lock_file):
    # Get the current time and the time when the lock file was last modified
    time_now = time.time()
    lock_file_time = os.path.getmtime(lock_file)

    # If the lock file is older than 45 seconds, delete it
    if lock_file_time < (time_now - 45):
        os.remove(lock_file)
    else:
        print("Another instance of the script is running. Please try again later.")
        exit(1)

# If lock file doesn't exist or is deleted, create a new lock file
with open(lock_file, 'w') as file:
    file.write("Lock file created.")


def delayed_sound():
    time.sleep(0.5)
    pyautogui.press('f22')
    winsound.PlaySound("*", winsound.SND_ALIAS)


# obtain audio from the microphone
r = sspeech_recognitionr.Recognizer()
with speech_recognition.Microphone() as source:
    t = threading.Thread(target=delayed_sound)
    t.start()
    audio = r.listen(source)
    t.join()

pyautogui.press('f22')
winsound.PlaySound("*", winsound.SND_ALIAS)
# recognize speech using Whisper API
with open('openaikey.txt', 'r') as key_file:
    OPENAI_API_KEY = key_file.read().strip()

try:
    text = r.recognize_whisper_api(audio, api_key=OPENAI_API_KEY)
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system",
             "content": 'Please correct punctuation on the following message, do not add or remove any words. ' +
                        'Ensure the punctuation is non agressive. In addition, replace any slang that is typed out ' +
                        'with more natural text based alternatives, for example: L-M-A-O would be replaced with lmao'},
            {"role": "user", "content": text}
        ])

    old_clipboard_content = clipboard.paste()
    clipboard.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    clipboard.copy(old_clipboard_content)

except speech_recognition.RequestError as e:
    pyautogui.typewrite("error")


# Clean up the lock file at the end
os.remove(lock_file)
