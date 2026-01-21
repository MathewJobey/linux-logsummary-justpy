import base64
import os

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