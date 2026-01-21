import base64
import os
import justpy as jp

def get_b64_image(file_path):
    """
    Reads an image file from the given path and converts it 
    to a base64 string for HTML display.
    """
    if not os.path.exists(file_path):
        return ""
        
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"[ERROR] Could not load image {file_path}: {e}")
        return ""

def setup_lightbox(wp):
    """
    Creates a hidden full-screen overlay attached to the webpage (wp).
    Returns the overlay div and the image tag so the main app can control them.
    """
    # 1. The Full-Screen Overlay (Hidden by default)
    # z-50 ensures it sits on top of everything
    lightbox = jp.Div(a=wp, classes="hidden fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4 cursor-zoom-out")
    
    # 2. The Image Container inside it
    lightbox_img = jp.Img(a=lightbox, classes="max-w-full max-h-full rounded shadow-2xl border-2 border-white")
    
    # 3. Click to Close Logic
    def close_lightbox(self, msg):
        # Simply hide it again
        lightbox.classes = "hidden fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4 cursor-zoom-out"
        
    lightbox.on('click', close_lightbox)
    
    return lightbox, lightbox_img