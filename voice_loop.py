#!/usr/bin/env python3
"""
Minimal push-to-talk loop for the Local Voice Chat Agent MVP.

Flow: microphone capture -> Whisper CLI transcription -> Ollama mistral:latest -> Piper TTS -> playback.
Requires `sounddevice` and `numpy` (see requirements.txt).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

try:
    import numpy as np
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover
    print(f"[x] Missing dependency: {exc}. Install requirements with `pip install -r requirements.txt`.", file=sys.stderr)
    sys.exit(1)
import shutil

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

WHISPER_BIN = BASE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = BASE_DIR / "whisper.cpp" / "models" / "ggml-small.bin"
WHISPER_DYLD_PARTS = [
    BASE_DIR / "whisper.cpp" / "build" / "src",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src" / "ggml-blas",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src" / "ggml-metal",
]

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:latest")
PIPER_MODEL = Path(os.environ.get("PIPER_MODEL", BASE_DIR / "en_US-lessac-medium.onnx"))

MIC_SAMPLE_RATE = 16_000
MIC_CHANNELS = 1


def _require_file(path: Path, description: str) -> None:
    if not path.exists():
        print(f"[x] Missing {description}: {path}", file=sys.stderr)
        sys.exit(1)


def record_utterance() -> Path | None:
    """Record audio until the user presses Enter. Returns path to the wav file."""
    print("Recording... Press Enter to stop.")
    stop_event = threading.Event()

    def wait_for_stop() -> None:
        input()
        stop_event.set()

    threading.Thread(target=wait_for_stop, daemon=True).start()

    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    frames: list[np.ndarray] = []

    def callback(indata, frames_count, time_info, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        audio_queue.put(indata.copy())

    with sd.InputStream(
        samplerate=MIC_SAMPLE_RATE,
        channels=MIC_CHANNELS,
        dtype="float32",
        callback=callback,
    ):
        while not stop_event.is_set():
            try:
                chunk = audio_queue.get(timeout=0.1)
                frames.append(chunk)
            except queue.Empty:
                continue

    if not frames:
        print("[!] No audio captured.")
        return None

    audio = np.concatenate(frames, axis=0)
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)

    timestamp = int(time.time())
    wav_path = ARTIFACT_DIR / f"utterance_{timestamp}.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(MIC_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(MIC_SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())

    print(f"[✓] Saved recording to {wav_path}")
    return wav_path


def transcribe(audio_path: Path) -> str:
    """Invoke Whisper CLI and return the transcript string."""
    env = os.environ.copy()
    dyld_paths = [str(p) for p in WHISPER_DYLD_PARTS if p.exists()]
    existing = env.get("DYLD_LIBRARY_PATH")
    if existing:
        dyld_paths.append(existing)
    env["DYLD_LIBRARY_PATH"] = ":".join(dyld_paths)

    cmd = [
        str(WHISPER_BIN),
        "-m",
        str(WHISPER_MODEL),
        "-f",
        str(audio_path),
        "-otxt",
    ]

    print("[…] Running Whisper transcription...")
    subprocess.run(cmd, check=True, cwd=str(BASE_DIR), env=env)
    txt_path = Path(f"{audio_path}.txt")  # whisper-cli appends ".txt" to original filename
    transcript = txt_path.read_text(encoding="utf-8").strip()
    print(f"[Whisper] {transcript}")
    return transcript


def build_prompt(history: list[tuple[str, str]], user_text: str) -> str:
    lines = [
        "You are Local Voice Chat Agent, a concise helpful companion. "
        "Answer conversationally in 1-3 sentences.",
    ]
    for role, content in history:
        lines.append(f"{role.upper()}: {content}")
    lines.append(f"USER: {user_text}")
    lines.append("ASSISTANT:")
    return "\n".join(lines)


def query_ollama(prompt: str) -> str:
    print(f"[…] Querying Ollama ({OLLAMA_MODEL})...")
    result = subprocess.run(
        ["ollama", "run", OLLAMA_MODEL],
        input=prompt,
        text=True,
        capture_output=True,
        check=True,
    )
    reply = result.stdout.strip()
    print(f"[Ollama] {reply}")
    return reply


def synthesize_speech(text: str) -> Path:
    output = ARTIFACT_DIR / f"response_{int(time.time())}.wav"
    cmd = [
        "piper",
        "--model",
        str(PIPER_MODEL),
        "--output_file",
        str(output),
    ]
    print("[…] Running Piper TTS...")
    subprocess.run(cmd, input=text, text=True, check=True, cwd=str(BASE_DIR))
    print(f"[Piper] Saved audio to {output}")
    return output


def play_audio(audio_path: Path) -> None:
    """Play audio using afplay (macOS) or fallback to stdout path."""
    if shutil.which("afplay"):
        subprocess.run(["afplay", str(audio_path)], check=True)
    elif shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(audio_path)], check=True)
    else:
        print(f"[i] Audio ready at {audio_path}; open it manually.")


def main() -> None:
    _require_file(WHISPER_BIN, "Whisper CLI binary (build whisper.cpp)")
    _require_file(WHISPER_MODEL, "Whisper model ggml-small.bin")
    _require_file(PIPER_MODEL, "Piper voice model")

    history: list[tuple[str, str]] = []
    print("Local Voice Chat Agent")
    print("Ensure `ollama serve` is running and Piper/Whisper paths are valid.")
    print("Controls: press Enter to start speaking, Enter again to stop, 'q' to quit.")

    while True:
        user_cmd = input("\nPress Enter to speak or type 'q' to quit: ").strip().lower()
        if user_cmd in {"q", "quit", "exit"}:
            print("Goodbye!")
            break

        audio_path = record_utterance()
        if not audio_path:
            continue

        try:
            transcript = transcribe(audio_path)
        except subprocess.CalledProcessError as exc:
            print(f"[x] Whisper failed: {exc}")
            continue

        if not transcript:
            print("[!] Empty transcript, skipping.")
            continue

        prompt = build_prompt(history, transcript)
        try:
            reply = query_ollama(prompt)
        except subprocess.CalledProcessError as exc:
            print(f"[x] Ollama error: {exc.stderr}")
            continue

        history.append(("user", transcript))
        history.append(("assistant", reply))

        try:
            audio_reply = synthesize_speech(reply)
            play_audio(audio_reply)
        except subprocess.CalledProcessError as exc:
            print(f"[x] Piper/playback error: {exc}")


if __name__ == "__main__":
    main()
