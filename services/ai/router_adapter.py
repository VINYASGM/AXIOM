from typing import Any, Dict, List, Optional
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from router import LLMRouter, ChatRequest, ChatMessage

class RouterRunnable(Runnable):
    """
    Adapter to make LLMRouter compatible with LangChain Runnable interface.
    Allows the router to be used in LangChain pipelines (e.g. prompt | router | parser).
    """
    
    def __init__(self, router: LLMRouter, model: str = "gpt-4-turbo"):
        self.router = router
        self.model = model
    
    def invoke(self, input: Any, config: Optional[RunnableConfig] = None) -> BaseMessage:
        raise NotImplementedError("Use ainvoke for async router")

    async def ainvoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs) -> BaseMessage:
        """
        Execute the router asynchronously.
        Accepts: List[BaseMessage] (standard LangChain input) or Dict
        Returns: BaseMessage
        """
        messages = []
        
        # normalized input to list of ChatMessage
        if isinstance(input, list):
            # List of BaseMessage
            for msg in input:
                role = "user"
                if msg.type == "system":
                    role = "system"
                elif msg.type == "ai":
                    role = "assistant"
                messages.append(ChatMessage(role=role, content=msg.content))
        elif isinstance(input, dict) and "messages" in input:
             # Dict input
             pass # Logic to handle dict input if needed, usually prompt templates return proper structures
        else:
             # Fallback string
             messages.append(ChatMessage(role="user", content=str(input)))

        # Create request
        request = ChatRequest(
            messages=messages,
            model=self.model,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2048)
        )
        
        # Execute via router
        response = await self.router.chat(request)
        
        # Convert back to LangChain BaseMessage (AIMessage)
        from langchain_core.messages import AIMessage
        return AIMessage(content=response.content)
