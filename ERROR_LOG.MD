# Error Log

## Phase 1

**Date:** 2023-10-27

- **No errors encountered.** The script for Phase 1 was developed and tested, and it performed as expected without any critical failures.

---

**Date:** 2023-10-28

- **Error:** Persistent failure to recover the embedded payload. The extraction process consistently reads a stream of '0's, which causes the marker verification to fail and prevents the creation of the output file.
  - **File:** `main.py`
  - **Functions:** `extract()`, `_bitstream_to_payload()`
  - **Trace:**
    ```
    --- 🔍 Starting Extraction Process ---
    ...
    ❌ Error: Marker not found! ... got 0000000000000000000000.
    ```
  - **Resolution (SOLVED):** The root cause was a series of subtle bugs. The final, critical flaw was a logic error in the single-pass extractor. The on-the-fly header parser would calculate a payload length based on the initial bits *before* validating that those bits contained the correct marker. On a stream of zeroes, it would calculate a length of 0 and stop, causing the marker validation to fail. The solution was to add a check to validate the marker *before* trusting the length, ensuring the extractor only proceeds if it has found a valid header.
- **Final Update:** The above fix to the script's logic was correct and necessary. However, it did not solve the problem. A final diagnostic test, separating the `embed` and `extract` functions into two separate processes, proved that the issue lies with `cv2.VideoWriter`. In the current environment, it is failing to write the modified frames to disk. The logic of the script is sound, but it is blocked by an environmental/dependency issue.

### Example Error Format

**Date:** YYYY-MM-DD

- **Error:** A brief, clear description of the error.
  - **File:** `path/to/file.py`
  - **Function:** `function_name()`
  - **Trace:** 
    ```
    Paste relevant traceback here.
    ```
  - **Resolution:** A clear explanation of how the error was fixed.
