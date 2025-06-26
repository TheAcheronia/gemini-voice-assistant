# Aether AI Voice Assistant - main.py
# A multi-feature, voice-commanded AI assistant for Windows 11.
# Features: Gemini-powered Q&A, web search, app launching, weather, time, and more.

import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import sys
import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import google.generativeai as genai

# --- Local Imports ---
try:
    import config
except ImportError:
    print("FATAL ERROR: config.py not found. Please create it and add your API keys.")
    sys.exit(1)

# --- Initialization ---
console = Console()

# Initialize Text-to-Speech Engine
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # You can change the voice index if you have multiple voices installed
    engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)
except Exception as e:
    console.print(f"[bold red]TTS Engine Error: {e}[/bold red]")
    console.print("[bold yellow]Text-to-speech will be disabled.[/bold yellow]")
    engine = None

# Initialize Speech Recognition
recognizer = sr.Recognizer()
# Adjust for ambient noise to improve accuracy
recognizer.energy_threshold = 300 
recognizer.pause_threshold = 0.8
recognizer.dynamic_energy_threshold = True

# --- API Configuration ---
# Configure Google Gemini AI
if config.GEMINI_API_KEY:
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        console.print(f"[bold red]Gemini AI Error: {e}[/bold red]")
        gemini_model = None
else:
    console.print("[bold yellow]Gemini API key not found. AI Q&A will be disabled.[/bold yellow]")
    gemini_model = None

# OpenWeatherMap API Key Check
if not config.OPENWEATHER_API_KEY:
    console.print("[bold yellow]OpenWeatherMap API key not found. Weather feature will be disabled.[/bold yellow]")


# --- Core Functions ---

def speak(text):
    """
    Converts text to speech and prints it to the console with styling.
    """
    console.print(Panel(Text(f"Aether: {text}", justify="left"), title="[bold cyan]Assistant[/bold cyan]", border_style="cyan"))
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            console.print(f"[bold red]TTS Error: {e}[/bold red]")

def listen_for_command():
    """
    Listens for a voice command from the user and converts it to text.
    """
    with sr.Microphone() as source:
        # FIX: Wrapped text in Text() object and applied justification there.
        console.print(Panel(Text("Listening...", justify="center", style="bold magenta"), border_style="magenta"))
        try:
            # Adjust for ambient noise once before listening
            # recognizer.adjust_for_ambient_noise(source, duration=1) 
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # FIX: Wrapped text in Text() object and applied justification there.
            console.print(Panel(Text("Recognizing...", justify="center", style="bold green"), border_style="green"))
            command = recognizer.recognize_google(audio).lower()
            console.print(Panel(Text(f"You: {command}", justify="left"), title="[bold green]User[/bold green]", border_style="green"))
            return command
        
        except sr.WaitTimeoutError:
            console.print("[bold yellow]Listening timed out. No command received.[/bold yellow]")
            return ""
        except sr.UnknownValueError:
            console.print("[bold yellow]Sorry, I didn't catch that. Please try again.[/bold yellow]")
            return ""
        except sr.RequestError as e:
            console.print(f"[bold red]Could not request results from Google Speech Recognition service; {e}[/bold red]")
            return ""
        except Exception as e:
            console.print(f"[bold red]An error occurred during listening: {e}[/bold red]")
            return ""

def get_weather(city):
    """
    Fetches and speaks the weather for a given city using OpenWeatherMap API.
    """
    if not config.OPENWEATHER_API_KEY:
        speak("I can't fetch the weather because the OpenWeatherMap API key is missing.")
        return

    api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={config.OPENWEATHER_API_KEY}&units=metric"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()

        if data["cod"] == 200:
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            speak(f"The current weather in {city} is {weather_desc} with a temperature of {temp} degrees Celsius.")
        else:
            speak(f"Sorry, I couldn't find the weather for {city}.")

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            speak("Weather check failed. The API key is invalid. Please check your configuration.")
        else:
            speak(f"An HTTP error occurred while fetching weather: {http_err}")
    except Exception as e:
        speak(f"An error occurred while fetching weather data: {e}")

def handle_gemini_query(query):
    """
    Sends a query to the Gemini AI model and speaks the response.
    """
    if not gemini_model:
        speak("I can't answer that as the Gemini AI service is not configured.")
        return
        
    try:
        # FIX: Wrapped text in Text() object and applied justification there.
        console.print(Panel(Text("Thinking with Gemini AI...", justify="center", style="bold blue"), border_style="blue"))
        response = gemini_model.generate_content(query)
        speak(response.text)
    except Exception as e:
        speak(f"Sorry, I encountered an error with the AI model: {e}")


def process_command(command):
    """
    Processes the user's command and performs the corresponding action.
    """
    if not command:
        return

    # --- Core Commands ---
    if "hello" in command or "hi aether" in command:
        speak("Hello! I am Aether, your AI assistant. How can I help you today?")

    elif "what's the time" in command or "what time is it" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {current_time}")

    elif "what's the date" in command or "what is today's date" in command:
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        speak(f"Today's date is {current_date}")

    elif "goodbye" in command or "exit" in command or "shut down" in command:
        speak("Goodbye! Shutting down.")
        sys.exit()

    # --- Application Launching ---
    elif "open notepad" in command:
        speak("Opening Notepad.")
        os.system("start notepad.exe")

    elif "open calculator" in command:
        speak("Opening Calculator.")
        os.system("start calc.exe")
        
    elif "open file explorer" in command:
        speak("Opening File Explorer.")
        os.system("start explorer.exe")

    # --- Web and API Commands ---
    elif "search for" in command:
        search_query = command.replace("search for", "").strip()
        url = f"https://www.google.com/search?q={search_query}"
        speak(f"Here are the search results for {search_query}.")
        webbrowser.open(url)
        
    elif "open youtube" in command:
        speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")

    elif "weather in" in command:
        city = command.split("weather in")[-1].strip()
        get_weather(city)
        
    # --- Fallback to Gemini AI ---
    else:
        # If the command is not recognized, treat it as a general question for Gemini.
        handle_gemini_query(command)


# --- Main Loop ---

def main():
    """
    The main function that runs the assistant loop.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(
        Text("Aether AI Voice Assistant", justify="center", style="bold blue"),
        subtitle="[cyan]Powered by Gemini[/cyan]",
        border_style="blue"
    ))
    speak("Aether is now online. Say 'hello' to begin, or give me a command.")
    
    while True:
        command = listen_for_command()
        if command:
            process_command(command)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted by user. Shutting down.[/bold red]")
        sys.exit(0)
