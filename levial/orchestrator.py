import sys
import time
import asyncio
import subprocess
import json
from typing import List, Tuple, Dict, Any, Callable
from pathlib import Path
import queue
import sounddevice as sd
import numpy as np
import threading
import time
import random

from .config import ConfigManager
from .audio import AudioCapture, AudioPlayer
from .asr import WhisperASR
from .tts import PiperTTS
from .llm import OllamaLLM
from .mcp_client import MCPClient
from .wake_word import WakeWordListener, SpeechDetector

from .memory.manager import MemoryManager

class InputListener:
    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self.thread = threading.Thread(target=self._input_loop, daemon=True)
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        # Cannot easily kill input(), so we just let it be daemon

    def _input_loop(self):
        print("Press 'q' + Enter at any time to quit.")
        while self.running:
            try:
                line = sys.stdin.readline()
                if line and line.strip().lower() in ['q', 'quit', 'exit']:
                    self.callback()
                    break
            except ValueError:
                pass

class ConversationOrchestrator:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.audio_capture = AudioCapture(
            sample_rate=self.config.mic_sample_rate,
            channels=self.config.mic_channels,
            max_duration_sec=self.config.recording_max_sec
        )
        self.asr = WhisperASR(
            bin_path=self.config.whisper_bin_path,
            model_path=self.config.whisper_model_path,
            base_dir=self.config.base_dir
        )
        self.tts = PiperTTS(
            model_path=self.config.piper_model_path,
            base_dir=self.config.base_dir
        )
        self.llm = OllamaLLM(model_name=self.config.llm_model_name)
        self.mcp_client = MCPClient(self.config.config_data)
        self.memory_manager = MemoryManager(self.config.base_dir)
        self.history: List[Tuple[str, str]] = []
        
        # Audio Player instance
        self.audio_player = AudioPlayer()

        # Wake Word & VAD
        self.wake_event = threading.Event()
        self.detected_wake_word = None
        
        def wake_callback(model_name: str):
            self.detected_wake_word = model_name
            self.wake_event.set()

        self.wake_listener = WakeWordListener(
            callback=wake_callback,
            model_paths=self.config.wake_word_model_paths
        )
        self.speech_detector = SpeechDetector()
        
        # Status Callback for WebSocket
        self.status_callback = None
        
        # Configurable Parameters
        self.silence_duration = 1.5  # Default value, can be updated via WebSocket
        self.proactivity_level = 0.0 # 0.0 to 1.0
        self.last_interaction_time = time.time()
        self.is_proactive_trigger = False
        
        # Shutdown Control
        self.shutdown_event = threading.Event()
        self.input_listener = InputListener(callback=self.shutdown_event.set)

    def set_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback for status updates (for WebSocket broadcasting)."""
        self.status_callback = callback

    def _emit_status(self, status: str, data: Dict[str, Any] = None):
        """Emit status update to WebSocket clients."""
        if self.status_callback:
            payload = {"status": status}
            if data:
                payload.update(data)
            self.status_callback(status, payload)

    def update_config(self, config: Dict[str, Any]):
        """Update orchestrator configuration dynamically."""
        if "silence_duration" in config:
            self.silence_duration = config["silence_duration"]
            print(f"[Config] Updated silence_duration to {self.silence_duration}s")
        if "proactivity_level" in config:
            self.proactivity_level = float(config["proactivity_level"])
            print(f"[Config] Updated proactivity_level to {self.proactivity_level}")

    def trigger_wake(self):
        """Manually trigger the wake word (e.g. from UI click)."""
        # Only trigger if we are waiting for wake word (IDLE state)
        if not self.wake_event.is_set():
            print("[!] Manual wake trigger received")
            self.detected_wake_word = "Manual Trigger"
            self.wake_event.set()

    async def start(self):
        """Async entry point to initialize MCP and run the loop."""
        print("Initializing MCP Client...")
        await self.mcp_client.start()
        
        self.input_listener.start()
        await self.run_loop()

        print("Shutting down MCP Client...")
        await self.mcp_client.stop()
        self.input_listener.stop()

    def run(self):
        """Entry point for the main script."""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            print("\nStopped by user.")

    def _get_audio_stream(self, q: queue.Queue):
        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            # Flatten to 1D array
            q.put(indata.flatten())
        
        return sd.InputStream(
            samplerate=16000, # openWakeWord expects 16k
            channels=1,
            dtype="int16",    # openWakeWord works best with int16
            blocksize=1280,   # Force 1280 samples per chunk (80ms)
            callback=callback
        )

    async def run_loop(self):
        print("Levial - Local Voice Assistant (v2.0 Agentic)")
        print("Say 'Hey Jarvis' (proxy for Levial) to wake me up.")
        print("Say 'Alexa' (proxy for Goodbye) to exit immediately.")
        print("Say 'Thank you' to stop speaking.")

        while not self.shutdown_event.is_set():
            # --- STATE: IDLE (Listening for Wake Word) ---
            print("[State] IDLE - Waiting for wake word...")
            self._emit_status("idle")
            self.wake_event.clear()
            self.detected_wake_word = None
            self.is_proactive_trigger = False
            
            audio_q = queue.Queue()
            stream = self._get_audio_stream(audio_q)
            
            def stream_callback(n):
                try:
                    return audio_q.get(timeout=0.1)
                except queue.Empty:
                    return None

            with stream:
                self.wake_listener.start(stream_callback)
                
                # Wait for wake word OR shutdown
                while not self.wake_event.is_set() and not self.shutdown_event.is_set():
                    self.wake_event.wait(timeout=0.5)
                    
                    # Proactivity Check
                    if self.proactivity_level > 0:
                        idle_time = time.time() - self.last_interaction_time
                        if idle_time > 30: # 30s minimum idle
                            # Chance check (runs every 0.5s)
                            # Max level (1.0) -> ~1% chance per 0.5s -> ~2% per sec -> ~50s avg wait
                            if random.random() < (self.proactivity_level * 0.01):
                                print(f"[Proactive] Triggered! Idle: {idle_time:.1f}s")
                                self.is_proactive_trigger = True
                                self.wake_event.set()
                
                self.wake_listener.stop()
            
            if self.shutdown_event.is_set():
                break

            if self.is_proactive_trigger:
                print(f"[!] Proactive Interaction Triggered")
                self._emit_status("wake_word_detected", {"wake_word": "Proactive"})
                # Skip listening and jump to generation
                # We construct a prompt for the agent to initiate conversation
                transcript = "System: The user has been idle. Initiate a conversation based on their interests."
            else:
                if self.detected_wake_word and "alexa" in self.detected_wake_word.lower():
                    print("[i] 'Alexa' detected - Pausing listening. Say 'Hey Jarvis' to resume.")
                    self._emit_status("idle")
                    continue  # Return to wake word listening instead of exiting
                
                # --- STATE: LISTENING (User Command) ---
                print("[State] LISTENING - Speak now...")
                self._emit_status("listening")
                timestamp = int(time.time())
                audio_path = self.config.artifacts_dir / f"utterance_{timestamp}.wav"
                
                # Define volume callback to emit status
                def volume_callback(level):
                    # Throttle updates to avoid flooding WebSocket? 
                    # For now, just emit. The frontend can handle it or we can throttle here.
                    # Let's throttle to every ~100ms if needed, but for now raw is fine for smoothness.
                    # Actually, let's scale it up a bit for visibility
                    scaled_level = min(level * 5, 1.0) 
                    self._emit_status("audio_level", {"level": scaled_level})
    
                # Record until silence
                recorded_path = await asyncio.to_thread(
                    self.audio_capture.record_until_silence, 
                    output_path=audio_path,
                    silence_threshold=0.01, # Adjust based on mic
                    silence_duration=self.silence_duration,
                    volume_callback=volume_callback
                )
                
                if self.shutdown_event.is_set():
                    break
                
                if not recorded_path:
                    print("[!] No audio recorded.")
                    continue
    
                try:
                    transcript = await asyncio.to_thread(self.asr.transcribe, recorded_path)
                except subprocess.CalledProcessError as exc:
                    print(f"[x] Whisper failed: {exc}")
                    continue

            if not transcript:
                print("[!] Empty transcript.")
                continue

            print(f"> User: {transcript}")
            self._emit_status("transcript", {"text": transcript})
            
            # Check for Termination
            if "goodbye" in transcript.lower():
                print("Goodbye!")
                break

            self.history.append(("user", transcript))
            
            # --- Memory Retrieval ---
            context = self.memory_manager.get_relevant_context(transcript)
            
            # Get User Preferences
            user_profile = self.memory_manager.user_profile.get_profile()
            preferences = user_profile.get("preferences", [])
            prefs_str = ", ".join(preferences) if preferences else ""
            
            # --- Agentic Loop ---
            max_turns = 5
            current_turn = 0
            
            while current_turn < max_turns and not self.shutdown_event.is_set():
                current_turn += 1
                
                tools_json = json.dumps(self.mcp_client.tools, indent=2)
                full_prompt = self.llm.build_prompt(self.history, transcript, context=context, tools_json=tools_json, user_preferences=prefs_str) 

                print(f"[State] THINKING (Turn {current_turn})...")
                self._emit_status("thinking", {"turn": current_turn})
                try:
                    reply = await asyncio.to_thread(self.llm.query, full_prompt)
                except subprocess.CalledProcessError as exc:
                    print(f"[x] Ollama error: {exc.stderr}")
                    break

                # Check for Tool Call (Same logic as before)
                try:
                    start_idx = reply.find('{')
                    end_idx = reply.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        potential_json = reply[start_idx:end_idx+1]
                        tool_call = json.loads(potential_json)
                        if "tool" in tool_call and "arguments" in tool_call:
                            tool_name = tool_call["tool"]
                            server_name = tool_call.get("server")
                            args = tool_call["arguments"]
                            print(f"[!] Tool Call: {tool_name} on {server_name}")
                            if server_name:
                                try:
                                    result = await self.mcp_client.call_tool(server_name, tool_name, args)
                                    observation = str(result)
                                except Exception as e:
                                    print(f"[!] Tool execution failed: {e}")
                                    observation = f"Error: Tool execution failed: {e}"
                            else:
                                observation = "Error: Server name missing."
                            self.history.append(("assistant", reply))
                            self.history.append(("system", f"Tool Output: {observation}"))
                            continue
                except json.JSONDecodeError:
                    pass

                print(f"> Assistant: {reply}")
                self._emit_status("response", {"text": reply})
                self.history.append(("assistant", reply))
                self.memory_manager.add_interaction("user", transcript)
                self.memory_manager.add_interaction("assistant", reply)
                
                # Extract and update knowledge using LLM
                try:
                    print("[State] EXTRACTING KNOWLEDGE...")
                    knowledge = self.memory_manager.extract_and_update_knowledge(
                        user_message=transcript,
                        assistant_message=reply,
                        llm_query_fn=lambda prompt: self.llm.query(prompt)
                    )
                    # Broadcast knowledge update to frontend
                    profile = self.memory_manager.user_profile.get_profile()
                    self._emit_status("knowledge_update", {
                        "profile": profile,
                        "latest_extraction": knowledge
                    })
                    print(f"[Knowledge] Updated: {knowledge}")
                except Exception as e:
                    print(f"[!] Knowledge extraction failed: {e}")
                
                # Break out of loop - we got a final answer (no tool call)
                break
            
            # --- STATE: SPEAKING (TTS) ---
            if reply:
                print(f"[State] SPEAKING: {reply}")
                self._emit_status("speaking")
                self.history.append(("agent", reply))
                
                # Update last interaction time
                self.last_interaction_time = time.time()
                
                # Generate TTS
                try:
                    audio_file = await asyncio.to_thread(self.tts.synthesize, reply, self.config.artifacts_dir)
                    self.audio_player.play(audio_file)
                except Exception as e:
                    print(f"[x] TTS Error: {e}")
                    
                    # Start Barge-In Monitoring
                    barge_q = queue.Queue()
                    barge_stream = self._get_audio_stream(barge_q)
                    
                    def barge_callback(n):
                        try:
                            return barge_q.get(timeout=0.1)
                        except queue.Empty:
                            return None

                    with barge_stream:
                        self.speech_detector.start(barge_callback)
                        
                        # Wait while playing OR speech detected OR shutdown
                        while self.audio_player.current_process and self.audio_player.current_process.poll() is None:
                            if self.shutdown_event.is_set():
                                self.audio_player.stop()
                                break
                                
                            if self.speech_detector.wait_for_speech(timeout=0.1):
                                print("[!] Barge-In Detected! Stopping TTS.")
                                self.audio_player.stop()
                                
                                # Capture the interruption
                                print("Listening to interruption...")
                                int_path = self.config.artifacts_dir / f"interruption_{int(time.time())}.wav"
                                break
                        
                        self.speech_detector.stop()
                    
                    if self.shutdown_event.is_set():
                        break

                    # If we broke out due to speech, record it
                    if self.audio_player.current_process is None and self.speech_detector.speech_detected_event.is_set():
                        # Stop detector to stop consuming queue
                        self.speech_detector.stop()
                        
                        # Get buffered audio (start of utterance)
                        frames = self.speech_detector.get_buffer()
                        
                        # Continue recording from the SAME queue until silence
                        print("Listening to interruption...")
                        silence_threshold = 0.01
                        silence_duration = 1.0
                        last_sound_time = time.time()
                        is_speaking = True # We know they started speaking
                        
                        while not self.shutdown_event.is_set():
                            try:
                                chunk = barge_q.get(timeout=0.1)
                                frames.append(chunk)
                                
                                # Silence Detection
                                rms = np.sqrt(np.mean(chunk**2))
                                if rms > silence_threshold:
                                    last_sound_time = time.time()
                                
                                if (time.time() - last_sound_time > silence_duration):
                                    print("[i] Silence detected.")
                                    break
                            except queue.Empty:
                                continue
                        
                        # Save combined audio
                        int_path = self.config.artifacts_dir / f"interruption_{int(time.time())}.wav"
                        int_recorded = self.audio_capture.save_audio(frames, int_path)
                        
                        if int_recorded:
                            int_text = await asyncio.to_thread(self.asr.transcribe, int_recorded)
                            print(f"> Interruption: {int_text}")
                            
                            if "thank you" in int_text.lower():
                                print("Stopped by user.")
                                break # Exit Turn Loop -> Go to IDLE
                            elif "goodbye" in int_text.lower():
                                print("Goodbye!")
                                self.shutdown_event.set()
                                break # Exit Turn Loop
                            else:
                                pass

                except subprocess.CalledProcessError as exc:
                    print(f"[x] Piper/playback error: {exc}")
