"use client";

import { useEffect, useRef, useState } from "react";

interface VoiceAgentState {
  status: "idle" | "wake_word_detected" | "listening" | "thinking" | "speaking" | "error";
  transcript: string;
  lastResponse: string;
  isConnected: boolean;
  agentRunning: boolean;
  wakeWord?: string;
  userProfile?: any;
  audioLevel?: number;
  micSensitivity: number;
  proactivityLevel: number;
}

export function useVoiceAgent() {
  // Load mic sensitivity from localStorage or use default (1.5)
  const [state, setState] = useState<VoiceAgentState>({
    status: "idle",
    transcript: "",
    lastResponse: "",
    isConnected: false,
    agentRunning: false,
    wakeWord: undefined,
    userProfile: undefined,
    audioLevel: 0,
    micSensitivity: typeof window !== "undefined" ? parseFloat(localStorage.getItem("micSensitivity") || "1.5") : 1.5,
    proactivityLevel: typeof window !== "undefined" ? parseFloat(localStorage.getItem("proactivityLevel") || "0") : 0,
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket("ws://localhost:8000/ws");

      ws.onopen = () => {
        setState((prev) => ({ ...prev, isConnected: true }));
        console.log("Connected to Levial Voice Agent");
      };

      ws.onclose = () => {
        setState((prev) => ({ ...prev, isConnected: false, status: "idle" }));
        console.log("Disconnected from Voice Agent, reconnecting in 3s...");
        // Reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (e) {
          console.error("Error parsing message:", e);
        }
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const handleMessage = (data: any) => {
    console.log("Received message:", data);
    
    switch (data.type) {
      case "connected":
        console.log(data.message);
        break;
      case "idle":
        setState((prev) => ({ ...prev, status: "idle" }));
        break;
      case "wake_word_detected":
        setState((prev) => ({ ...prev, status: "wake_word_detected", wakeWord: data.wake_word }));
        playDing();
        break;
      case "listening":
        setState((prev) => ({ ...prev, status: "listening" }));
        break;
      case "thinking":
        setState((prev) => ({ ...prev, status: "thinking" }));
        break;
      case "speaking":
        setState((prev) => ({ ...prev, status: "speaking" }));
        break;
      case "transcript":
        setState((prev) => ({ ...prev, transcript: data.text }));
        break;
      case "response":
        setState((prev) => ({ ...prev, lastResponse: data.text }));
        break;
      case "knowledge_update":
        setState((prev) => ({ ...prev, userProfile: data.profile }));
        console.log("Knowledge updated:", data.profile);
        break;
      case "audio_level":
        setState((prev) => ({ ...prev, audioLevel: data.level }));
        break;
      case "error":
        setState((prev) => ({ ...prev, status: "error" }));
        console.error("Voice Agent Error:", data.message);
        break;
      case "agent_started":
        setState((prev) => ({ ...prev, agentRunning: true, status: "idle" }));
        console.log("Agent started");
        break;
      case "agent_stopped":
        setState((prev) => ({ ...prev, agentRunning: false, status: "idle" }));
        console.log("Agent stopped");
        break;
    }
  };

  const playDing = () => {
    const audio = new Audio("data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU"); // Short placeholder
    // Using a better base64 for a pleasant ding
    // Actually, let's use a real generated beep for now to ensure it works
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime); // A5
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.1);
    
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
    
    osc.start();
    osc.stop(ctx.currentTime + 0.1);
  };

  const updateKnowledge = (updates: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "update_knowledge",
        updates: updates
      }));
      console.log("Sent knowledge update:", updates);
    } else {
      console.error("WebSocket not connected, cannot update knowledge");
    }
  };

  const updateConfig = (config: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "update_config",
        config: config
      }));
      console.log("Sent config update:", config);
    } else {
      console.error("WebSocket not connected, cannot update config");
    }
  };

  const setMicSensitivity = (value: number) => {
    setState((prev) => ({ ...prev, micSensitivity: value }));
    if (typeof window !== "undefined") {
      localStorage.setItem("micSensitivity", value.toString());
    }
    updateConfig({ silence_duration: value });
  };

  const setProactivityLevel = (value: number) => {
    setState((prev) => ({ ...prev, proactivityLevel: value }));
    if (typeof window !== "undefined") {
      localStorage.setItem("proactivityLevel", value.toString());
    }
    updateConfig({ proactivity_level: value });
  };

  const triggerAgent = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "trigger_wake"
      }));
      console.log("Sent manual wake trigger");
    } else {
      console.error("WebSocket not connected, cannot trigger agent");
    }
  };

  const startAgent = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "start_agent"
      }));
      console.log("Sent start agent request");
    } else {
      console.error("WebSocket not connected, cannot start agent");
    }
  };

  const stopAgent = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "stop_agent"
      }));
      console.log("Sent stop agent request");
    } else {
      console.error("WebSocket not connected, cannot stop agent");
    }
  };

  return {
    ...state,
    updateKnowledge,
    updateConfig,
    setMicSensitivity,
    setProactivityLevel,
    triggerAgent,
    startAgent,
    stopAgent,
  };
}
