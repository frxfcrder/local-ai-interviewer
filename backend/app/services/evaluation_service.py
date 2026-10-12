from typing import List, Dict, AsyncGenerator
from app.services.llm_service import LLMService
from app.prompts.evaluator import EVALUATOR_SYSTEM_PROMPT

class EvaluationService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def generate_evaluation(self, conversation_history: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        Takes the complete interview chat history, constructs the evaluation payload,
        and streams the structured critique from the local LLM.
        """
        # Build messages payload with evaluator system prompt
        messages = [{"role": "system", "content": EVALUATOR_SYSTEM_PROMPT}]
        
        # Format the chat history into a readable transcript format for the evaluator
        formatted_transcript = "\n".join(
            [f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')}" for msg in conversation_history]
        )
        
        messages.append({
            "role": "user",
            "content": f"Here is the complete transcript of the technical interview session. Please evaluate the candidate:\n\n{formatted_transcript}"
        })

        async for chunk in self.llm_service.generate_stream(messages):
            yield chunk