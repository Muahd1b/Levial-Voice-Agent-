import subprocess
from typing import List, Tuple

class OllamaLLM:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def build_prompt(self, history: List[Tuple[str, str]], user_text: str, context: str = "", tools_json: str = "", user_preferences: str = "") -> str:
        system_prompt = (
            "You are Levial, a capable and intelligent voice assistant. "
            "You have access to external tools to help the user. "
            "Use these tools silently and naturally to fulfill requests. "
            "Do NOT list your tools or explain your capabilities unless explicitly asked. "
            "Answer conversationally and concisely (1-3 sentences)."
        )
        
        lines = [system_prompt]
        
        if user_preferences:
            lines.append(f"IMPORTANT - ADAPT TO USER PREFERENCES: {user_preferences}")
        
        if tools_json:
            lines.append(f"\nAVAILABLE TOOLS (Use JSON to call):\n{tools_json}\n")
            lines.append("To call a tool, output ONLY a JSON object: {\"tool\": \"tool_name\", \"server\": \"server_name\", \"arguments\": {...}}")

        if context:
            lines.append(f"\nCONTEXT:\n{context}\n")
            
        for role, content in history:
            lines.append(f"{role.upper()}: {content}")
        lines.append(f"USER: {user_text}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)

    def query(self, prompt: str) -> str:
        print(f"[…] Querying Ollama ({self.model_name})...")
        result = subprocess.run(
            ["ollama", "run", self.model_name],
            input=prompt,
            text=True,
            capture_output=True,
            check=True,
        )
        reply = result.stdout.strip()
        print(f"[Ollama] {reply}")
        return reply
