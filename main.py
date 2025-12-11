import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
from PIL import Image
import os

DTMF_FREQS = {
    '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
    '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
    '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
    '0': (941, 1336)
}


SAMPLE_RATE = 8000
BLOCK_SIZE = 205
SILENCE_THRESHOLD = 0.025
MIN_DURATION = 0.04
DIGIT_IMAGES_PATH = "Number"

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs):
    b, a = butter_bandpass(lowcut, highcut, fs)
    y = lfilter(b, a, data)
    return y

def detect_dtmf_number(audio_file):
    try:
        fs, data = wavfile.read(audio_file)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        data = data / np.max(np.abs(data))
        digits = []
        pos = 0
        last_digit = None
        digit_count = 0

        while pos + BLOCK_SIZE <= len(data):
            segment = data[pos:pos + BLOCK_SIZE]

            if np.max(np.abs(segment)) > SILENCE_THRESHOLD:
                digit = advanced_analysis(segment, fs)
                if digit:
                    if digit == last_digit:
                        digit_count += 1
                    else:
                        if last_digit and (digit_count * BLOCK_SIZE / fs >= MIN_DURATION):
                            digits.append(last_digit)
                        last_digit = digit
                        digit_count = 1
                    pos += BLOCK_SIZE // 2
                    continue

            pos += BLOCK_SIZE // 4

        if last_digit and (digit_count * BLOCK_SIZE / fs >= MIN_DURATION):
            digits.append(last_digit)

        return ''.join(digits)
    except Exception as e:
        print(f"Error processing {audio_file}: {str(e)}")
        return ""

def advanced_analysis(segment, fs):
    row_freqs = [697, 770, 852, 941]
    col_freqs = [1209, 1336, 1477]

    row_energies = []
    for freq in row_freqs:
        filtered = bandpass_filter(segment, freq - 20, freq + 20, fs)
        energy = np.sum(filtered ** 2)
        row_energies.append(energy)

    col_energies = []
    for freq in col_freqs:
        filtered = bandpass_filter(segment, freq - 20, freq + 20, fs)
        energy = np.sum(filtered ** 2)
        col_energies.append(energy)

    row_idx = np.argmax(row_energies)
    col_idx = np.argmax(col_energies)

    row_freq = row_freqs[row_idx]
    col_freq = col_freqs[col_idx]

    for digit, (row, col) in DTMF_FREQS.items():
        if abs(row - row_freq) <= 15 and abs(col - col_freq) <= 15:
            return digit

    return None

def create_output_image(digits, output_path):
    try:
        digit_images = []
        for digit in digits:
            img_path = os.path.join(DIGIT_IMAGES_PATH, f"{digit}.png")
            if os.path.exists(img_path):
                digit_images.append(Image.open(img_path))

        if not digit_images:
            raise ValueError("No digit images found")

        widths, heights = zip(*(img.size for img in digit_images))
        total_width = sum(widths)
        max_height = max(heights)

        result = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        x_offset = 0

        for img in digit_images:
            result.paste(img, (x_offset, 0))
            x_offset += img.size[0]

        result.save(output_path, quality=95)
        print(f"Saved output image: {output_path}")
    except Exception as e:
        print(f"Error creating image: {str(e)}")

def process_files():
    audio_files = [
        "dialing1.wav", "dialing2.wav", "dialing3.wav", "dialing4.wav",
        "realDialing1.wav", "realDialing2.wav", "realDialing3.wav", "realDialing4.wav"
    ]

    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            print(f"File not found: {audio_file}")
            continue

        print(f"\nProcessing: {audio_file}")
        digits = detect_dtmf_number(audio_file)
        print(f"Detected: {digits}")

        if digits:
            output_file = f"result_{os.path.splitext(audio_file)[0]}.png"
            create_output_image(digits, output_file)

if __name__ == "__main__":
    if os.path.exists(DIGIT_IMAGES_PATH):
        process_files()
    else:
        print(f"Directory {DIGIT_IMAGES_PATH} not found!")