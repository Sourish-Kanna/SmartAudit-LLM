from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

class ChatSession:
    def __init__(self, system_prompt: str, model):
        self.messages: list[HumanMessage | SystemMessage | AIMessage] = [SystemMessage(content=system_prompt)]
        self.model = model

    def user_chat(self, message: str) -> str:
        # Add user message
        self.messages.append(HumanMessage(content=message))

        # Invoke model
        response = self.model.invoke(self.messages)

        # Add model response to history
        self.messages.append(AIMessage(content=response.content))

        return response.content
