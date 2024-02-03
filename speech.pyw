#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class
import threading
import time
import pyautogui
import speech_recognition as sr
import winsound
import openai
import clipboard
def delayed_sound():
    time.sleep(0.5)
    pyautogui.press('f22')
    winsound.PlaySound("*", winsound.SND_ALIAS)
# obtain audio from the microphone
r = sr.Recognizer()
with sr.Microphone() as source:
    t = threading.Thread(target=delayed_sound)
    t.start()
    audio = r.listen(source)
    t.join()

pyautogui.press('f22')
winsound.PlaySound("*", winsound.SND_ALIAS)
# recognize speech using Whisper API
with open('openaikey.txt','r') as key_file:
    OPENAI_API_KEY = key_file.read().strip()

try:
    text = r.recognize_whisper_api(audio, api_key=OPENAI_API_KEY)
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": 'Please correct punctuation on the following message, do not add or remove any words. Ensure the punctuation is non agressive. In addition, replace any slang that is typed out with more natural text based alternatives, for example: L-M-A-O would be replaced with lmao'},
            {"role": "user", "content": text}
        ])

    old_clipboard_content = clipboard.paste()  
    clipboard.copy(text)  
    pyautogui.hotkey('ctrl', 'v')  
    clipboard.copy(old_clipboard_content)

except sr.RequestError as e:
    pyautogui.typewrite("error")

