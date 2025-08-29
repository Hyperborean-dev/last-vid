import cv2
import numpy as np
import hashlib
import os

# --- Constants ---
MARKER = b'VCiph_START'
DCT_COORDINATE = (2, 1)
QUANTIZATION_STEP = 4 

def _payload_to_bitstream(payload_path):
    """Reads a file and converts it into a bitstream with a header."""
    with open(payload_path, 'rb') as f:
        payload_data = f.read()
    payload_length_bytes = len(payload_data).to_bytes(4, byteorder='big')
    header = MARKER + payload_length_bytes
    full_data = header + payload_data
    bitstream = ''.join(format(byte, '08b') for byte in full_data)
    print(f"✅ Payload loaded: {len(payload_data):,} bytes.")
    print(f"✅ Header constructed: {len(header)} bytes (Marker + 4-byte length).")
    print(f"✅ Total bitstream length: {len(bitstream):,} bits.")
    return bitstream

def _bitstream_to_payload(bitstream, output_path):
    """Converts a bitstream back to bytes and saves it to a file."""
    byte_array = bytearray(int(bitstream[i:i+8], 2) for i in range(0, len(bitstream), 8))
    marker_len = len(MARKER)
    header_len = marker_len + 4
    if len(byte_array) < header_len:
        print("❌ Error: Not enough data extracted to read header.")
        return False
    extracted_marker = byte_array[:marker_len]
    if extracted_marker != MARKER:
        print(f"❌ Error: Marker not found! Expected {MARKER.hex()}, got {extracted_marker.hex()}.")
        return False
    print("✅ Marker verified successfully.")
    length_bytes = byte_array[marker_len:header_len]
    payload_length = int.from_bytes(length_bytes, byteorder='big')
    print(f"✅ Payload length from header: {payload_length:,} bytes.")
    payload_data = byte_array[header_len : header_len + payload_length]
    if len(payload_data) != payload_length:
        print(f"❌ Error: Payload incomplete. Expected {payload_length} bytes, got {len(payload_data)}.")
        return False
    with open(output_path, 'wb') as f:
        f.write(payload_data)
    print(f"✅ Payload of {len(payload_data):,} bytes written to '{output_path}'.")
    return True

def embed(video_path, payload_path, output_path):
    """Embeds a payload using a robust quantization scheme."""
    print("\n--- 🎬 Starting Embedding Process ---")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open input video file: {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    bitstream = _payload_to_bitstream(payload_path)
    bitstream_iterator = iter(bitstream)
    frame_count = 0
    bits_embedded = 0
    embedding_complete = False
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1
        if not embedding_complete:
            ycbcr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            y_channel = ycbcr_frame[:, :, 0]
            for i in range(0, height, 8):
                for j in range(0, width, 8):
                    try:
                        bit_to_embed = next(bitstream_iterator)
                        block_uint8 = y_channel[i:i+8, j:j+8]
                        block_float32 = block_uint8.astype(np.float32)
                        dct_block = cv2.dct(block_float32)
                        coeff = dct_block[DCT_COORDINATE]
                        q = QUANTIZATION_STEP
                        if bit_to_embed == '0':
                            dct_block[DCT_COORDINATE] = round(coeff / q) * q
                        else:
                            dct_block[DCT_COORDINATE] = round((coeff - q/2) / q) * q + q/2
                        idct_block_float32 = cv2.idct(dct_block)
                        modified_block_uint8 = np.clip(idct_block_float32, 0, 255).astype(np.uint8)
                        y_channel[i:i+8, j:j+8] = modified_block_uint8
                        bits_embedded += 1
                    except StopIteration:
                        embedding_complete = True
                        break
                if embedding_complete: break
            ycbcr_frame[:, :, 0] = y_channel
            modified_frame = cv2.cvtColor(ycbcr_frame, cv2.COLOR_YCrCb2BGR)
            writer.write(modified_frame)
        else:
            writer.write(frame)
    cap.release()
    writer.release()
    writer = None
    
    if not embedding_complete:
        print(f"\n⚠️ WARNING: End of video reached but only {bits_embedded:,} of {len(bitstream):,} bits were embedded.")
    else:
        print(f"\n✅ Embedding complete. {bits_embedded:,} bits embedded in {frame_count} frames.")
    print(f"✅ Stego video saved to '{output_path}'.")

def extract(video_path, output_path):
    """Extracts a payload using a robust, single-pass method with proper validation."""
    print("\n--- 🔍 Starting Extraction Process (Single-Pass, Validated) ---")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open stego video file: {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    header_len_bits = (len(MARKER) + 4) * 8
    total_bits_to_extract = None
    extracted_bits = []
    
    extraction_failed = False
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Video ended before extraction could be completed.")
            break
        
        y_channel = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)[:, :, 0]
        
        for i in range(0, height, 8):
            for j in range(0, width, 8):
                block_float32 = y_channel[i:i+8, j:j+8].astype(np.float32)
                dct_block = cv2.dct(block_float32)
                coeff = dct_block[DCT_COORDINATE]
                q = QUANTIZATION_STEP
                nearest_zero = round(coeff / q) * q
                nearest_one = round((coeff - q/2) / q) * q + q/2
                dist_to_zero = abs(coeff - nearest_zero)
                dist_to_one = abs(coeff - nearest_one)
                extracted_bits.append('0' if dist_to_zero <= dist_to_one else '1')

                if total_bits_to_extract is None and len(extracted_bits) >= header_len_bits:
                    header_bitstream = "".join(extracted_bits)
                    header_bytes = bytearray(int(header_bitstream[k:k+8], 2) for k in range(0, len(header_bitstream), 8))
                    
                    # --- THE CRITICAL FIX ---
                    # We MUST validate the marker here before trusting the length
                    if header_bytes[:len(MARKER)] != MARKER:
                        print(f"❌ Error: Marker not found at the beginning of the stream. Stopping.")
                        extraction_failed = True
                        break # Breaks inner loop
                    # --- END FIX ---
                        
                    payload_len = int.from_bytes(header_bytes[len(MARKER):len(MARKER)+4], 'big')
                    total_bits_to_extract = header_len_bits + (payload_len * 8)
                    print(f"✅ Header parsed. Total data size: {total_bits_to_extract:,} bits.")
                
                if total_bits_to_extract and len(extracted_bits) >= total_bits_to_extract:
                    break
            if extraction_failed or (total_bits_to_extract and len(extracted_bits) >= total_bits_to_extract):
                break

    cap.release()
    cap = None
    
    if not extraction_failed:
        print(f"✅ Extraction complete. {len(extracted_bits):,} bits recovered.")
        _bitstream_to_payload("".join(extracted_bits), output_path)

def get_file_hash(filepath):
    """Calculates the MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

if __name__ == '__main__':
    INPUT_VIDEO = 'input/cover.mp4'
    SECRET_PAYLOAD = 'input/secret.zip'
    STEGO_VIDEO = 'output/stego_video.mp4'
    RECOVERED_PAYLOAD = 'output/recovered_secret.zip'
    os.makedirs('input', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    if not os.path.exists(SECRET_PAYLOAD):
        print(f"❌ Error: Secret payload '{SECRET_PAYLOAD}' not found. Please create it.")
        exit()
    if not os.path.exists(INPUT_VIDEO):
        print(f"❌ Error: Cover video '{INPUT_VIDEO}' not found. Please place it in the input folder.")
        exit()
    embed(INPUT_VIDEO, SECRET_PAYLOAD, STEGO_VIDEO)
    extract(STEGO_VIDEO, RECOVERED_PAYLOAD)
    print("\n--- 💯 Verifying Integrity ---")
    if os.path.exists(RECOVERED_PAYLOAD):
        original_hash = get_file_hash(SECRET_PAYLOAD)
        recovered_hash = get_file_hash(RECOVERED_PAYLOAD)
        print(f"Original hash:  {original_hash}")
        print(f"Recovered hash: {recovered_hash}")
        if original_hash == recovered_hash:
            print("\n✅ SUCCESS: The recovered file is a perfect bit-for-bit match!")
        else:
            print("\n❌ FAILURE: The recovered file is corrupted. Hashes do not match.")
    else:
        print(f"\n❌ FAILURE: The recovered file '{RECOVERED_PAYLOAD}' was not created.")