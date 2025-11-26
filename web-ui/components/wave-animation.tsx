"use client";

import { motion } from "framer-motion";
import { Mic } from "lucide-react";

interface WaveAnimationProps {
  status: string;
  audioLevel?: number;
}

export function WaveAnimation({ status, audioLevel = 0 }: WaveAnimationProps) {
  const variants = {
    idle: {
      scale: [1, 1.05, 1],
      opacity: 0.5,
      transition: { duration: 2, repeat: Infinity },
    },
    wake_word_detected: {
      scale: [1, 1.2, 1],
      opacity: 1,
      borderColor: "rgba(59, 130, 246, 0.8)", // Blue
      boxShadow: "0 0 20px rgba(59, 130, 246, 0.5)",
      transition: { duration: 0.5 },
    },
    listening: {
      scale: [1 + audioLevel * 0.5, 1 + audioLevel * 1.5, 1 + audioLevel * 0.5], // Pulse effect + dynamic scaling
      opacity: [0.8, 1, 0.8],
      borderColor: "rgba(34, 197, 94, 0.9)", // Brighter Green
      boxShadow: [
        `0 0 ${20 + audioLevel * 30}px rgba(34, 197, 94, 0.4)`,
        `0 0 ${30 + audioLevel * 60}px rgba(34, 197, 94, 0.7)`,
        `0 0 ${20 + audioLevel * 30}px rgba(34, 197, 94, 0.4)`
      ],
      transition: { duration: 1.5, repeat: Infinity }, // Smooth pulsing
    },
    thinking: {
      scale: [1, 0.9, 1],
      rotate: [0, 180, 360],
      opacity: 0.8,
      borderColor: "rgba(168, 85, 247, 0.8)", // Purple
      borderRadius: ["50%", "40%", "50%"],
      transition: { duration: 2, repeat: Infinity },
    },
    speaking: {
      scale: [1, 1.15, 1],
      opacity: 1,
      borderColor: "rgba(239, 68, 68, 0.8)", // Red
      boxShadow: "0 0 25px rgba(239, 68, 68, 0.5)",
      transition: { duration: 0.8, repeat: Infinity },
    },
    error: {
      scale: 1,
      opacity: 0.5,
      backgroundColor: "#ef4444",
    },
  };

  const getAnimationState = () => {
    return status;
  };

  const getStatusText = () => {
    switch (status) {
      case "idle":
        return 'Say "Hey Jarvis" to wake me up';
      case "wake_word_detected":
        return "Wake word detected!";
      case "listening":
        return "I'm listening...";
      case "thinking":
        return "Thinking...";
      case "speaking":
        return "Speaking...";
      case "error":
        return "Error";
      default:
        return status;
    }
  };

  return (
    <div className="relative flex items-center justify-center h-64 w-64">
      {/* Outer waves */}
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          className={`absolute rounded-full ${status === "error" ? "bg-red-500" : "bg-primary"}`}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={variants[getAnimationState() as keyof typeof variants]}
          transition={{
            duration: status === "thinking" ? 1 : status === "wake_word_detected" ? 0.5 : 2,
            repeat: Infinity,
            delay: index * 0.3,
            ease: "easeInOut",
          }}
          style={{
            width: `${200 - index * 30}px`,
            height: `${200 - index * 30}px`,
          }}
        />
      ))}

      {/* Center icon */}
      <motion.div
        className={`absolute z-10 rounded-full p-8 shadow-lg ${status === "error" ? "bg-red-500" : "bg-primary"}`}
        animate={{
          scale: status === "speaking" ? [1, 1.1, 1] : status === "listening" ? 1.05 : 1,
        }}
        transition={{
          duration: 0.5,
          repeat: status === "speaking" ? Infinity : 0,
        }}
      >
        <Mic className="h-12 w-12 text-primary-foreground" />
      </motion.div>

      {/* Status text */}
      <div className="absolute -bottom-8 text-center w-full">
        <motion.p
          className="text-sm font-medium text-muted-foreground"
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {getStatusText()}
        </motion.p>
      </div>
    </div>
  );
}
