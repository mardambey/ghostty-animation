#!/usr/bin/env python3

import time
import sys
import signal
import getpass
import pwd
import os
import subprocess
import termios
import tty
import logging
import traceback
from datetime import datetime

# ANSI escape codes
WHITE = '\033[37m'
BLUE = '\033[34m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Setup logging with more detailed configuration
logging.basicConfig(
    filename='terminal_lock.log',
    level=logging.DEBUG,  # Capture all levels of logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_ip_address():
    try:
        if sys.platform == 'darwin':  # macOS
            cmd = "ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | xargs"
            return subprocess.getoutput(cmd).strip() or 'unknown'
        else:  # Linux
            return subprocess.getoutput('hostname -I').strip() or 'unknown'
    except:
        return 'unknown'

def log_attempt(success, method='unknown'):
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
        ip = get_ip_address()
        hostname = subprocess.getoutput('hostname').strip() or 'unknown'
        msg = f"Exit attempt by {user} from {hostname} ({ip}) - {'SUCCESS' if success else 'FAILED'} using {method}"
        logging.info(msg)
    except Exception as e:
        logging.error(f"Failed to log attempt: {str(e)}\n{traceback.format_exc()}")

def getch():
    # Get a single character without echoing
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def draw_password_prompt():
    # Box dimensions
    width = 50
    height = 7
    
    # Box characters (double-line box drawing)
    top_left = '╔'
    top_right = '╗'
    bottom_left = '╚'
    bottom_right = '╝'
    horizontal = '═'
    vertical = '║'
    
    # Clear screen
    sys.stdout.write('\033[2J\033[H')
    
    # Calculate vertical centering
    v_padding = '\n' * 10
    sys.stdout.write(v_padding)
    
    # Draw box
    h_offset = (80 - width) // 2
    
    # Draw top
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{top_left}{horizontal * (width-2)}{top_right}\n")
    
    # Empty line
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{vertical}{' ' * (width-2)}{vertical}\n")
    
    # Title line
    title = "[ Authentication Required ]"
    title_padding = (width - 2 - len(title)) // 2
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{vertical}{' ' * title_padding}{title}{' ' * (width - 2 - title_padding - len(title))}{vertical}\n")
    
    # Empty line
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{vertical}{' ' * (width-2)}{vertical}\n")
    
    # Input field line
    field = "[ " + "_" * 20 + " ]"
    field_padding = (width - 2 - len(field)) // 2
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{vertical}{' ' * field_padding}{field}{' ' * (width - 2 - field_padding - len(field))}{vertical}\n")
    
    # Empty line
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{vertical}{' ' * (width-2)}{vertical}\n")
    
    # Bottom of box
    sys.stdout.write(' ' * h_offset)
    sys.stdout.write(f"{bottom_left}{horizontal * (width-2)}{bottom_right}\n")
    
    # Calculate exact cursor position for input field
    cursor_x = h_offset + field_padding + 3 + 1  # +3 for margin and '[ '
    cursor_y = 14+1  # 10 (v_padding) + 4 (lines to input field)
    
    # Position cursor exactly at first underscore
    sys.stdout.write(f"\033[{cursor_y};{cursor_x}H")
    sys.stdout.flush()
    
    return (cursor_x, cursor_y)

def get_hidden_input(prompt):
    cursor_x, cursor_y = draw_password_prompt()
    password = ''
    field_pos = 0
    
    while True:
        char = getch()
        if char == '\r' or char == '\n':  # Enter pressed
            return password
        elif char == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        elif char == '\x7f':  # Backspace
            if password:
                password = password[:-1]
                field_pos -= 1
                # Reposition cursor and update character
                sys.stdout.write(f"\033[{cursor_y};{cursor_x + field_pos}H")
                sys.stdout.write('_')
                sys.stdout.write(f"\033[{cursor_y};{cursor_x + field_pos}H")
        elif len(password) < 20:  # Max field width
            password += char
            # Reposition cursor and write asterisk
            sys.stdout.write(f"\033[{cursor_y};{cursor_x + field_pos}H")
            sys.stdout.write('*')
            field_pos += 1
        sys.stdout.flush()

def verify_password():
    try:
        # Get current user
        current_user = pwd.getpwuid(os.getuid()).pw_name
        
        # Try Linux password verification first
        try:
            import spwd
            import crypt
            password_hash = spwd.getspnam(current_user).sp_pwd
            password = get_hidden_input("Enter your password to exit: ")
            crypted = crypt.crypt(password, password_hash)
            success = crypted == password_hash
            log_attempt(success, 'Linux shadow password')
            return success
        except ImportError:
            # If crypt/spwd not available, fall back to macOS dscl
            password = get_hidden_input("Enter your password to exit: ")
            cmd = ['dscl', '.', '-authonly', current_user, password]
            result = subprocess.run(cmd, capture_output=True)
            success = result.returncode == 0
            log_attempt(success, 'macOS dscl')
            return success
            
    except (KeyboardInterrupt, EOFError):
        log_attempt(False, 'interrupted')
        return False
    except Exception as e:
        log_attempt(False, f'error: {str(e)}')
        return False

def sigint_handler(signum, frame):
    # Ignore Ctrl+C
    pass

def render_frame(frame_content):
    try:
        # Convert <span class="b"> tags to ANSI blue+bold
        frame = frame_content.replace('<span class="b">', BLUE + BOLD)
        frame = frame.replace('</span>', RESET + WHITE)
        
        # Clear screen and move cursor to top
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.write(WHITE + frame)  # Start with white text
        sys.stdout.flush()
    except Exception as e:
        logging.error(f"Frame rendering error: {str(e)}\n{traceback.format_exc()}")
        raise

def play_animation():
    frame_rate = 1/24  # 24 fps
    current_frame = 1
    
    try:
        # Install signal handler
        #signal.signal(signal.SIGINT, sigint_handler)
        
        # Log start of session
        logging.info(f"Terminal lock started by {pwd.getpwuid(os.getuid()).pw_name}")
        
        while True:
            try:
                for frame_num in range(current_frame, 236):
                    try:
                        frame_path = f'./animation_frames/frame_{frame_num:03d}.txt'
                        if not os.path.exists(frame_path):
                            logging.error(f"Missing animation frame: {frame_path}")
                            continue
                            
                        with open(frame_path, "r") as f:
                            frame = f.read()
                        render_frame(frame)
                        time.sleep(frame_rate)
                        current_frame = frame_num
                    except Exception as e:
                        logging.error(f"Error processing frame {frame_num}: {str(e)}\n{traceback.format_exc()}")
                        continue
                
                # Reset frame counter when we reach the end
                current_frame = 1
                
            except KeyboardInterrupt:
                # Clear screen for password prompt
                sys.stdout.write('\033[2J\033[H')
                sys.stdout.flush()
                
                # On Ctrl+C, verify password
                if verify_password():
                    sys.stdout.write(RESET)
                    sys.stdout.flush()
                    logging.info(f"Terminal lock ended by {pwd.getpwuid(os.getuid()).pw_name}")
                    sys.exit(0)
                
                # If password verification fails, continue animation from last frame
                continue
                
    except Exception as e:
        logging.critical(f"Critical animation error: {str(e)}\n{traceback.format_exc()}")
        raise

if __name__ == '__main__':
    try:
        # Log Python version and system info at startup
        logging.info(f"Python Version: {sys.version}")
        logging.info(f"Platform: {sys.platform}")
        logging.info(f"Working Directory: {os.getcwd()}")
        
        play_animation()
    except Exception as e:
        # Log the error with full traceback
        logging.critical(f"Fatal error: {str(e)}\n{traceback.format_exc()}")
        # Reset colors on any error
        sys.stdout.write(RESET)
        sys.stdout.flush()
        raise e
