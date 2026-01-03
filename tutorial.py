import justpy as jp
import webbrowser
import threading
from clean_card import build_clean_card

def app():
    wp = jp.WebPage()
    wp.classes = "bg-gray-100 min-h-screen flex items-center justify-center p-6"
    build_clean_card(wp)
    return wp

# auto-open in browser (optional)
threading.Thread(target=lambda: webbrowser.open("http://127.0.0.1:8000"), daemon=True).start()
jp.justpy(app)

