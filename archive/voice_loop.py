#!/usr/bin/env python3
"""
Minimal push-to-talk loop for the Local Voice Chat Agent MVP.

Flow: microphone capture -> Whisper CLI transcription -> Ollama mistral:latest -> Piper TTS -> playback.
Requires `sounddevice` and `numpy` (see requirements.txt).
"""

from __future__ import annotations

import json
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

def load_config() -> dict:
    config_path = Path(os.environ.get("LVCA_CONFIG", BASE_DIR / "config" / "default.json"))
    if not config_path.exists():
        print(f"[x] Config file not found: {config_path}. Create one or set LVCA_CONFIG.", file=sys.stderr)
        sys.exit(1)
    with config_path.open() as fh:
        config = json.load(fh)

    profile_name = os.environ.get("LVCA_PROFILE", config.get("active_profile"))
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        print(f"[x] Profile '{profile_name}' missing in config.", file=sys.stderr)
        sys.exit(1)

    profile = profiles[profile_name]
    print(f"[config] Loaded profile '{profile_name}': {profile.get('description', '')}")

    return {
        "profile_name": profile_name,
        "profile": profile,
        "artifacts_dir": Path(config.get("artifacts_dir", "artifacts")),
        "wake_word": config.get("wake_word", {}),
        "timeouts": config.get("timeouts", {}),
    }

CONFIG = load_config()
PROFILE = CONFIG["profile"]
ARTIFACT_DIR = (BASE_DIR / CONFIG["artifacts_dir"]).resolve()
ARTIFACT_DIR.mkdir(exist_ok=True)

WHISPER_BIN = BASE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = BASE_DIR / PROFILE.get("whisper_model", "whisper.cpp/models/ggml-small.bin")
WHISPER_DYLD_PARTS = [
    BASE_DIR / "whisper.cpp" / "build" / "src",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src" / "ggml-blas",
    BASE_DIR / "whisper.cpp" / "build" / "ggml" / "src" / "ggml-metal",
]

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", PROFILE.get("llm_model", "mistral:latest"))
PIPER_MODEL = Path(os.environ.get("PIPER_MODEL", BASE_DIR / PROFILE.get("piper_model", "en_US-lessac-medium.onnx")))

MIC_SAMPLE_RATE = PROFILE.get("mic_sample_rate", 16_000)
MIC_CHANNELS = PROFILE.get("mic_channels", 1)
MAX_HISTORY_TURNS = PROFILE.get("max_history_turns", 6)
RECORDING_MAX_SEC = CONFIG["timeouts"].get("recording_max_sec")


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

    start_time = time.time()

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
            if RECORDING_MAX_SEC and (time.time() - start_time) >= RECORDING_MAX_SEC:
                print(f"[i] Recording limit reached ({RECORDING_MAX_SEC}s).")
                stop_event.set()

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


class VoiceAgent:
    def __init__(self):
        self.is_running = False
        self.is_listening = False
        self.history: list[tuple[str, str]] = []
        self.status_callback = None
        self.stop_event = threading.Event()
        self.listen_thread = None

    def set_status_callback(self, callback):
        self.status_callback = callback

    def _emit_status(self, status: str, data: dict = None):
        if self.status_callback:
            self.status_callback(status, data)

    def start(self):
        self.is_running = True
        print("[VoiceAgent] Started")

    def stop(self):
        self.is_running = False
        self.stop_listening()
        print("[VoiceAgent] Stopped")

    def start_listening(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.stop_event.clear()
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        self._emit_status("listening")
        print("[VoiceAgent] Start listening")

    def stop_listening(self):
        if not self.is_listening:
            return
        self.is_listening = False
        self.stop_event.set()
        if self.listen_thread:
            self.listen_thread.join(timeout=1.0)
        self._emit_status("idle")
        print("[VoiceAgent] Stop listening")

    def _listen_loop(self):
        # This is a simplified version of the original record_utterance logic
        # adapted to run in a thread and check stop_event
        audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        frames: list[np.ndarray] = []

        def callback(indata, frames_count, time_info, status):
            if status:
                print(f"[audio] {status}", file=sys.stderr)
            audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=MIC_SAMPLE_RATE,
                channels=MIC_CHANNELS,
                dtype="float32",
                callback=callback,
            ):
                while not self.stop_event.is_set():
                    try:
                        chunk = audio_queue.get(timeout=0.1)
                        frames.append(chunk)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"[x] Audio recording error: {e}")
            self._emit_status("error", {"message": str(e)})
            return

        if not frames:
            return

        self._emit_status("processing")
        
        # Process audio
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

        self._process_utterance(wav_path)

    def _process_utterance(self, audio_path: Path):
        try:
            transcript = transcribe(audio_path)
            if not transcript:
                self._emit_status("idle")
                return
            
            self._emit_status("transcript", {"text": transcript})

            prompt = build_prompt(self.history, transcript)
            reply = query_ollama(prompt)
            
            self._emit_status("response", {"text": reply})

            self.history.append(("user", transcript))
            self.history.append(("assistant", reply))
            if MAX_HISTORY_TURNS and len(self.history) > MAX_HISTORY_TURNS:
                self.history = self.history[-MAX_HISTORY_TURNS:]

            self._emit_status("speaking")
            audio_reply = synthesize_speech(reply)
            play_audio(audio_reply)
            self._emit_status("idle")

        except Exception as e:
            print(f"[x] Processing error: {e}")
            self._emit_status("error", {"message": str(e)})
            self._emit_status("idle")

def main() -> None:
    # Legacy main for CLI usage
    agent = VoiceAgent()
    agent.start()
    
    _require_file(WHISPER_BIN, "Whisper CLI binary (build whisper.cpp)")
    _require_file(WHISPER_MODEL, f"Whisper model {WHISPER_MODEL}")
    _require_file(PIPER_MODEL, f"Piper voice model {PIPER_MODEL}")

    print("Local Voice Chat Agent (CLI Mode)")
    print("Controls: press Enter to start speaking, Enter again to stop, 'q' to quit.")

    while True:
        user_cmd = input("\nPress Enter to speak or type 'q' to quit: ").strip().lower()
        if user_cmd in {"q", "quit", "exit"}:
            break
        
        agent.start_listening()
        input("Press Enter to stop recording...")
        agent.stop_listening()

if __name__ == "__main__":
    main()
