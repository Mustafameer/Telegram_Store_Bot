import requests
import os
import shutil

os.makedirs('fonts', exist_ok=True)

# Google Fonts 'static' folder for TTF
fonts = {
    'Cairo-Bold.ttf': 'https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Bold.ttf',
    'Cairo-Regular.ttf': 'https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Regular.ttf'
}

for name, url in fonts.items():
    print(f"Downloading {name}...")
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(f'fonts/{name}', 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            print(f"Success: fonts/{name}")
        else:
            print(f"Failed {name}: Status {r.status_code}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Copy Arial as fallback
try:
    if os.path.exists(r"C:\Windows\Fonts\arial.ttf"):
        shutil.copy(r"C:\Windows\Fonts\arial.ttf", "fonts/arial.ttf")
        print("Copied Arial.ttf")
    if os.path.exists(r"C:\Windows\Fonts\arialbd.ttf"):
        shutil.copy(r"C:\Windows\Fonts\arialbd.ttf", "fonts/arialbd.ttf")
        print("Copied ArialBd.ttf")
except Exception as e:
    print(f"Failed to copy Arial: {e}")
