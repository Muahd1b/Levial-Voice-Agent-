# Levial - Local Voice Chat Agent

Levial is a fully local, privacy-preserving voice assistant that runs entirely on your personal machine. It integrates speech-to-text, a local Large Language Model (LLM), and text-to-speech to create a seamless voice interaction experience.

## Features

- **100% Local**: No audio or text leaves your device.
- **Low Latency**: Optimized for fast response times.
- **Modular Architecture**: Built with `whisper.cpp` (ASR), `Ollama` (LLM), and `Piper` (TTS).
- **Configurable Profiles**: Easily switch between "Snappy", "Balanced", and "Quality" profiles to match your hardware.
- **Wake Word Detection**: Always-on wake word support with "Hey Jarvis" (or custom wake words).
- **Web UI**: Modern Next.js interface with real-time WebSocket communication.
- **Memory System**: Persistent user profile and conversation memory with vector search.

## Prerequisites

- **macOS** (primary support) or Linux.
- **Python 3.10+**
- **Ollama**: Installed and running (`ollama serve`).
- **Node.js 18+**: For the web UI.
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
    - **Piper**: Download Piper voice model and place in `models/piper/`:
      ```bash
      # Run the included script to download models
      python scripts/download_models.py
      ```
      Or manually place `en_US-lessac-medium.onnx` and its JSON config in `models/piper/`.

## Directory Structure

```
voice-agent/
├── levial/              # Main Python package
│   ├── agents/          # Agent implementations
│   ├── memory/          # Memory system (vector store, user profile)
│   ├── tools/           # MCP tools (calendar, email, etc.)
│   └── ...
├── web-ui/              # Next.js web interface
├── models/              # ML model files
│   └── piper/           # Piper TTS models
├── data/                # Runtime data
│   ├── artifacts/       # Generated audio files
│   ├── chroma_db/       # Vector database
│   └── user_profile.json # User profile data
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── tests/               # Test files
├── config/              # Configuration files
└── whisper.cpp/         # Whisper ASR (external)
```

## Usage

### Start the Voice Agent with Web UI

1.  **Start Ollama** (if not already running):

    ```bash
    ollama serve
    ```

2.  **Start the backend server:**

    ```bash
    source .venv/bin/activate
    python server.py
    ```

3.  **Start the web UI** (in a new terminal):

    ```bash
    cd web-ui
    npm install  # First time only
    npm run dev
    ```

4.  **Open your browser** and navigate to `http://localhost:3000`

### Command Line Mode

To use the voice agent without the web UI:

```bash
source .venv/bin/activate
python -m levial.main
```

### Configuration

Configuration is managed via `config/default.json`. You can customize:

- **Profiles**: Adjust models and parameters for different performance needs.
- **Wake Word**: Settings for wake word detection.
- **Timeouts**: Adjust silence detection and processing timeouts.
- **MCP Servers**: Enable/disable various tool integrations.

You can override the default configuration file by setting the `LVCA_CONFIG` environment variable:

```bash
LVCA_CONFIG=/path/to/custom_config.json python server.py
```

To select a specific profile (e.g., `snappy`):

```bash
LVCA_PROFILE=snappy python server.py
```

## Architecture

- **`levial/orchestrator.py`**: Central state machine managing the conversation flow.
- **`levial/audio.py`**: Handles audio input/output.
- **`levial/asr.py`**: Wrapper for Whisper ASR.
- **`levial/llm.py`**: Wrapper for Ollama LLM.
- **`levial/tts.py`**: Wrapper for Piper TTS.
- **`levial/memory/`**: Memory management with vector store and user profiles.
- **`server.py`**: FastAPI/WebSocket server for web UI integration.

## License

[MIT License](LICENSE)
