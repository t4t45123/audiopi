from PIL import Image, ImageDraw, ImageFont
import os, sys
from time import sleep

WIDTH, HEIGHT = 360, 240
FONT = ImageFont.load_default()

books = [
    {"title": "Book One", "chapters": ["Intro", "Chapter 1", "Chapter 2"], "progress": (1, 0.5), "image": "book1.jpg", "chapter_lengths": [180, 600, 420]},
    {"title": "Book Two", "chapters": ["Start", "Middle", "End"], "progress": (0, 0.1), "image": "book1.jpg", "chapter_lengths": [180, 600, 420]},
]

menu_state = "title_select"  # title_select, now_playing, chapter_select, bluetooth
selected_index = 0
current_book = 0

def draw_menu(items, title="Menu", selected=0):
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)

    margin_top = 30
    spacing = 30
    draw.text((10, 10), title, font=FONT, fill="white")

    for i, item in enumerate(items):
        y = margin_top + i * spacing
        if i == selected:
            draw.rectangle([5, y - 2, WIDTH - 5, y + 18], fill="white")
            draw.text((10, y), item, font=FONT, fill="black")
        else:
            draw.text((10, y), item, font=FONT, fill="white")
    img.show()

def format_time(seconds):
    hours = int (seconds) // 3600
    minutes = (int(seconds) %3600) // 60
    secs = int(seconds) % 60
    return f"{minutes:02}:{secs:02}"

def draw_play_pause(draw, x, y, is_playing):
    if is_playing:
        # Play: Draw right-facing triangle
        draw.polygon([(x, y), (x, y + 12), (x + 10, y + 6)], fill=0)
    else:
        # Pause: Draw two vertical bars
        draw.rectangle([x, y, x + 3, y + 12], fill=0)
        draw.rectangle([x + 7, y, x + 10, y + 12], fill=0)

def draw_now_playing(book, is_playing=True):
    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((10, 5), book["title"], font=FONT, fill=0)

    # Book cover
    try:
        cover = Image.open(os.path.join("assets", "book_images", book["image"])).convert("1")
        cover = cover.resize((60, 90))
        img.paste(cover, (WIDTH - 70, 25))
    except:
        draw.rectangle([WIDTH - 70, 25, WIDTH - 10, 115], fill=1, outline=0)
        draw.line([WIDTH - 70, 25, WIDTH - 10, 115], fill=0)
        draw.line([WIDTH - 70, 115, WIDTH - 10, 25], fill=0)

    # Chapter info
    ch_idx, ch_prog = book["progress"]
    chapter = book["chapters"][ch_idx]
    draw.text((10, HEIGHT - 40), f"Chapter: {chapter} ({ch_idx + 1}/{len(book['chapters'])})", font=FONT, fill=0)

    # Play/Pause icon
    draw_play_pause(draw, WIDTH - 25, HEIGHT - 48, is_playing)

    # Progress bar
    bar_margin = 10
    bar_y = HEIGHT - 22
    bar_width = WIDTH - 2 * bar_margin
    bar_height = 8
    draw.rectangle([bar_margin, bar_y, bar_margin + bar_width, bar_y + bar_height], outline=0, fill=1)
    filled = int(bar_width * ch_prog)
    if filled > 0:
        draw.rectangle([bar_margin, bar_y, bar_margin + filled, bar_y + bar_height], fill=0)

    # Time display (centered below progress bar)
    total_seconds = book["chapter_lengths"][ch_idx]
    current_seconds = total_seconds * ch_prog
    time_text = f"{format_time(current_seconds)} / {format_time(total_seconds)}"
    bbox = draw.textbbox((0, 0), time_text, font=FONT)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT - 12), time_text, font=FONT, fill=0)

    img.show()

def draw_bluetooth_menu(selected=0):
    devices = ["Device A", "Device B", "Device C"]
    draw_menu(devices, "Bluetooth Devices", selected)

def handle_input():
    try:
        import msvcrt
        key = msvcrt.getch()
        if key == b'\xe0':  # arrow keys
            arrow = msvcrt.getch()
            return {b'H': 'up', b'P': 'down', b'M': 'right', b'K': 'left'}.get(arrow, None)
        elif key == b'\r':
            return 'enter'
        elif key == b'\x1b':
            return 'esc'
    except ImportError:
        return input("Input (w/s/enter/esc): ").lower()

def main():
    global menu_state, selected_index, current_book
    while True:
        os.system("cls" if os.name == "nt" else "clear")

        if menu_state == "title_select":
            draw_menu([b["title"] for b in books], "Select a Book", selected_index)
        elif menu_state == "now_playing":
            draw_now_playing(books[current_book])
        elif menu_state == "chapter_select":
            draw_menu(books[current_book]["chapters"], "Select Chapter", selected_index)
        elif menu_state == "bluetooth":
            draw_bluetooth_menu(selected_index)

        key = handle_input()

        item_count = (
            len(books) if menu_state == "title_select"
            else len(books[current_book]["chapters"]) if menu_state == "chapter_select"
            else 3 if menu_state == "bluetooth"
            else 0
        )

        if key == 'up':
            selected_index = (selected_index - 1) % item_count
        elif key == 'down':
            selected_index = (selected_index + 1) % item_count
        elif key == 'enter':
            if menu_state == "title_select":
                current_book = selected_index
                selected_index = 0
                menu_state = "now_playing"
            elif menu_state == "chapter_select":
                books[current_book]["progress"] = (selected_index, 0.0)
                menu_state = "now_playing"
            elif menu_state == "bluetooth":
                menu_state = "now_playing"
        elif key == 'esc':
            if menu_state == "now_playing":
                menu_state = "title_select"
                selected_index = 0
            else:
                menu_state = "now_playing"

        sleep(0.1)

if __name__ == "__main__":
    main()