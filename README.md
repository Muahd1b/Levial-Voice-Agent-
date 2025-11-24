# Levial - Local Voice Chat Agent

Levial is a fully local, privacy-preserving voice assistant that runs entirely on your personal machine. It integrates speech-to-text, a local Large Language Model (LLM), and text-to-speech to create a seamless voice interaction experience.

## Features

- **100% Local**: No audio or text leaves your device.
- **Low Latency**: Optimized for fast response times.
- **Modular Architecture**: Built with `whisper.cpp` (ASR), `Ollama` (LLM), and `Piper` (TTS).
- **Configurable Profiles**: Easily switch between "Snappy", "Balanced", and "Quality" profiles to match your hardware.
- **Push-to-Talk & Wake Word**: Supports both interaction modes (Wake Word currently in development).

## Prerequisites

- **macOS** (primary support) or Linux.
- **Python 3.10+**
- **Ollama**: Installed and running (`ollama serve`).
- **C/C++ Compiler**: For building `whisper.cpp`.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd voice-agent
    ```

2.  **Set up the Python environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Build Whisper.cpp:**

    ```bash
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    cmake -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build -j
    cd ..
    ```

    _Note: Ensure you have the required models for whisper.cpp in `whisper.cpp/models/`._

4.  **Download Models:**
    - **Ollama**: `ollama pull mistral:latest`
    - **Piper**: Ensure `en_US-lessac-medium.onnx` and its JSON config are in the root directory.

## Usage

To start the voice agent:

```bash
source .venv/bin/activate
python -m levial.main
```

### Configuration

Configuration is managed via `config/default.json`. You can customize:

- **Profiles**: Adjust models and parameters for different performance needs.
- **Wake Word**: Settings for wake word detection.
- **Timeouts**: Adjust silence detection and processing timeouts.

You can override the default configuration file by setting the `LVCA_CONFIG` environment variable:

```bash
LVCA_CONFIG=/path/to/custom_config.json python -m levial.main
```

To select a specific profile (e.g., `snappy`):

```bash
LVCA_PROFILE=snappy python -m levial.main
```

## Architecture

- **`levial/orchestrator.py`**: Central state machine managing the conversation flow.
- **`levial/audio.py`**: Handles audio input/output.
- **`levial/asr.py`**: Wrapper for Whisper ASR.
- **`levial/llm.py`**: Wrapper for Ollama LLM.
- **`levial/tts.py`**: Wrapper for Piper TTS.

## License

[MIT License](LICENSE)
