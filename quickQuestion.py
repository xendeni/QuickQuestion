import base64
import sys
import time
import threading
from io import BytesIO

try:
    import mss
except ImportError:
    sys.exit("pip install mss")
try:
    from PIL import Image
except ImportError:
    sys.exit("pip install Pillow")
try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install openai")
try:
    from pynput import mouse, keyboard
except ImportError:
    sys.exit("pip install pynput")

API_KEY = "enter ur api key from openai or just slightly alter code if you have another api key provider"
MODEL   = "gpt-4o" #lightweight af but still good enough to give correct answers
HOTKEY  = keyboard.Key.f9 #self explainatory no

def pick_point(label: str) -> tuple:
    print(f"  -> choose {label} and left click.")
    coords = []

    def on_click(x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            coords.append((x, y))
            return False

    with mouse.Listener(on_click=on_click) as l:
        l.join()

    x, y = coords[0]
    print(f"     Got: ({x}, {y})")
    return x, y


def select_region() -> tuple:
    print("\nregion setup")
    x1, y1 = pick_point("pos1")
    time.sleep(0.3)
    x2, y2 = pick_point("pos2")

    x      = min(x1, x2)
    y      = min(y1, y2)
    width  = abs(x2 - x1)
    height = abs(y2 - y1)

    print(f"\n  locked: ({x}, {y})  {width}x{height} px")
    print("  f9 to capture, ctrl+c to quit\n")
    return x, y, width, height



def capture(x: int, y: int, width: int, height: int) -> Image.Image:
    with mss.mss() as sct:
        mon = {"top": y, "left": x, "width": width, "height": height}
        raw = sct.grab(mon)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def image_to_b64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def ask_openai(img: Image.Image) -> str:
    client = OpenAI(api_key=API_KEY)
    b64 = image_to_b64(img)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a question helper"
                    "The user will show you a screenshot containing a question"
                    "Reply with ONLY the answer ,no explanation, no restating the question, "
                    "no filler. Pure answer only."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What is the answer?"
                    }
                ],
            },
        ],
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()



def handle_capture(region: tuple):
    x, y, w, h = region
    try:
        print("capture success", end=" ", flush=True)
        img = capture(x, y, w, h)
        print("asking gpt", end=" ", flush=True)
        answer = ask_openai(img)
        print(f"\n>>> {answer}\n")
    except Exception as e:
        print(f"\n[Error] {e}\n")


def run(region: tuple):
    def on_press(key):
        if key == HOTKEY:
            # Run in a separate thread so the keyboard listener doesn't crash
            t = threading.Thread(target=handle_capture, args=(region,), daemon=True)
            t.start()

    with keyboard.Listener(on_press=on_press) as l:
        try:
            l.join()
        except KeyboardInterrupt:
            print("\nBye!")



if __name__ == "__main__":
    print("screenask")
    region = select_region()
    run(region)
