from typing import Callable, Any, Dict, List
import inspect
from pydantic import BaseModel

class Tool(BaseModel):
    name: str
    description: str
    func: Callable
    
    class Config:
        arbitrary_types_allowed = True

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str):
        def decorator(func: Callable):
            self.tools[name] = Tool(
                name=name,
                description=description,
                func=func
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Tool:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self.tools.values()]

registry = ToolRegistry()
