#!/usr/bin/env python3

import time
import sys

# ANSI escape codes
BLUE = '\033[34m'
WHITE = '\033[37m'
BOLD = '\033[1m'
RESET = '\033[0m'

def render_frame(frame_content):
    # Convert <span class="b"> tags to ANSI blue+bold
    frame = frame_content.replace('<span class="b">', BLUE + BOLD)
    frame = frame.replace('</span>', RESET + WHITE)
    
    # Clear screen and move cursor to top
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.write(WHITE + frame)  # Start with white text
    sys.stdout.flush()

def play_animation():
    frame_rate = 1/24  # 24 fps
    while True:
        for frame_num in range(1, 236):
            with open(f'./animation_frames/frame_{frame_num:03d}.txt') as f:
                frame = f.read()
            render_frame(frame)
            time.sleep(frame_rate)

if __name__ == '__main__':
    try:
        play_animation()
    except KeyboardInterrupt:
        # Reset colors on exit
        sys.stdout.write(RESET)
        sys.stdout.flush()
