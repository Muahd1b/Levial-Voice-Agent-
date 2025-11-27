import logging
import time
from typing import Dict, Any, List
from pathlib import Path

from .vector_store import VectorStore
from .user_profile import UserProfile

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, base_dir: Path):
        """
        Initialize the Memory Manager.
        
        Args:
            base_dir: Base directory for storing memory artifacts.
        """
        self.memory_dir = base_dir / "data"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.vector_store = VectorStore(str(self.memory_dir / "chroma_db"))
        self.user_profile = UserProfile(str(self.memory_dir / "user_profile.json"))

    def add_interaction(self, role: str, content: str):
        """
        Add a conversation turn to episodic memory.
        """
        timestamp = int(time.time())
        metadata = {
            "role": role,
            "timestamp": timestamp,
            "type": "conversation"
        }
        # Use a simple ID strategy for now
        mem_id = f"{timestamp}_{role}"
        self.vector_store.add_memory(content, metadata, mem_id)

    def get_relevant_context(self, query: str) -> str:
        """
        Retrieve relevant context from both Vector Store and User Profile.
        """
        # 1. Get explicit profile data
        profile = self.user_profile.get_profile()
        profile_str = f"User Profile: {profile}"
        
        # 2. Get Current Time Context
        current_time_str = time.strftime("%A, %B %d, %Y %I:%M %p")
        time_context = f"Current Time: {current_time_str}"
        
        # 2. Get episodic memories
        memories = self.vector_store.search_memory(query, n_results=3)
        memory_str = ""
        if memories:
            memory_str = "\nRelevant Past Conversations:\n"
            for mem in memories:
                memory_str += f"- {mem['metadata'].get('role', 'unknown')}: {mem['text']}\n"
        
        return f"{time_context}\n{profile_str}\n{memory_str}"

    def extract_and_update_knowledge(self, user_message: str, assistant_message: str, llm_query_fn) -> Dict[str, Any]:
        """
        Extract knowledge from the conversation using LLM and update user profile.
        
        Args:
            user_message: What the user said
            assistant_message: What the assistant responded
            llm_query_fn: Function to call LLM (e.g., lambda prompt: ollama_llm.query(prompt))
        
        Returns:
            Dict with extracted knowledge
        """
        extraction_prompt = f"""Based on this conversation, extract any facts about the user that should be remembered.

User: {user_message}
Assistant: {assistant_message}

Extract ONLY factual information about the user (name, preferences, interests, locations, relationships, etc.).
Format your response as JSON:
{{
  "facts": {{
    "key": "value"
  }},
  "interests": ["topic1", "topic2"],
  "name": "their name if mentioned"
}}

If nothing new was learned, return: {{"facts": {{}}, "interests": [], "name": null}}
Only extract information explicitly stated or strongly implied. Do not make assumptions.
"""
        
        try:
            # Call LLM to extract knowledge
            result = llm_query_fn(extraction_prompt)
            
            # Parse JSON from response
            import json
            # Try to find JSON in the response
            start_idx = result.find('{')
            end_idx = result.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx+1]
                knowledge = json.loads(json_str)
                
                # Update user profile with extracted knowledge
                if knowledge.get("name"):
                    self.user_profile.profile_data["name"] = knowledge["name"]
                
                if knowledge.get("facts"):
                    for key, value in knowledge["facts"].items():
                        self.user_profile.profile_data["facts"][key] = value
                
                if knowledge.get("interests"):
                    for interest in knowledge["interests"]:
                        self.user_profile.update_interest(interest)
                
                # Save the updated profile
                self.user_profile.save_profile()
                
                logger.info(f"Extracted knowledge: {knowledge}")
                return knowledge
            else:
                logger.warning("No JSON found in LLM response for knowledge extraction")
                return {"facts": {}, "interests": [], "name": None}
                
        except Exception as e:
            logger.error(f"Knowledge extraction failed: {e}")
            return {"facts": {}, "interests": [], "name": None}

    def update_knowledge(self, updates: Dict[str, Any]):
        """
        Manually update the user profile.
        
        Args:
            updates: Dictionary containing updates (name, interests, facts)
        """
        try:
            if "name" in updates:
                self.user_profile.profile_data["name"] = updates["name"]
            
            if "interests" in updates:
                self.user_profile.profile_data["interests"] = updates["interests"]
                
            if "facts" in updates:
                # Merge facts instead of overwriting entirely if possible, 
                # but for simplicity let's allow full overwrite if passed
                self.user_profile.profile_data["facts"] = updates["facts"]
                
            self.user_profile.save_profile()
            logger.info(f"Manual profile update: {updates}")
            return self.user_profile.get_profile()
        except Exception as e:
            logger.error(f"Manual profile update failed: {e}")
            raise e
