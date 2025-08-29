# Phase 1: Core Functionality Test

This project is a minimal, monolithic implementation of a DCT-based video steganography system.

The **only goal** of this phase is to prove that we can embed data into a video and extract it again with **100% bit-for-bit accuracy** on a local file.

## 🎯 Architecture

- **`main.py`**: A single script containing all embedding and extraction logic. This avoids architectural complexity and makes debugging the core data flow straightforward.
- **No external dependencies** other than `numpy` and `opencv-python`.

## ⚙️ How to Run

1.  **Set up the environment:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Prepare your files:**
    - Place your cover video at `input/cover.mp4`.
    - Place your secret file at `input/secret.txt`.
    - *(Note: The script will create dummy files if these are missing, but using a real video is recommended).*

3.  **Run the script:**
    ```bash
    python3 main.py
    ```

## ✅ Expected Outcome

The script will perform three steps:
1.  **Embed** `input/secret.txt` into `input/cover.mp4`, creating `output/stego_video.mp4`.
2.  **Extract** the hidden data from `output/stego_video.mp4` into `output/recovered_secret.txt`.
3.  **Verify** that the MD5 hash of the original and recovered files match.

The final output should be: