"""Agent implementation with tool calling and structured output."""
import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import ValidationError

from models import FinalAnswer
from tools import TOOLS


class Agent:
    """Agent that can use tools to answer questions."""
    
    def __init__(
        self,
        model: str = "gpt-5-mini",
        max_iterations: int = 6,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.max_iterations = max_iterations
        # Initialize OpenAI client with explicit parameters to avoid proxy issues
        client_kwargs = {
            "api_key": api_key or os.getenv("OPENAI_API_KEY")
        }
        # Only add api_key if it's not None
        if not client_kwargs["api_key"]:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        self.client = OpenAI(**client_kwargs)
        self.conversation_history: List[Dict[str, Any]] = []
        
    def _get_system_prompt(self, is_final_round: bool = False) -> str:
        """Generate system prompt based on whether it's the final round."""
        base_prompt = """你是一个顶级的软件工程师和代码库专家。你的任务是回答关于代码库或文件系统的问题。

你可以使用以下工具来帮助你探索：

1. cat(file_path: str): 读取文件内容
   例如: cat(file_path="src/main.py")

2. ls(dir_path: str): 列出目录中的文件和子目录
   例如: ls(dir_path="src")

3. find(pattern: str, start_path: str): 根据文件名模式查找文件
   例如: find(pattern="*.py", start_path="src")

请遵循 "思考 -> 行动 -> 观察 -> 思考..." 的循环来解决问题。"""
        
        if is_final_round:
            return base_prompt + "\n\n这是最后一轮，你必须根据已经收集到的所有信息给出最终答案。不要再调用任何工具。"
        else:
            return base_prompt + f"\n\n你最多有{self.max_iterations}轮机会来调用工具。"
    
    def _format_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Format tools for OpenAI API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            }
            for tool_name, tool_info in TOOLS.items()
        ]
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        if tool_name not in TOOLS:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        tool_func = TOOLS[tool_name]["function"]
        try:
            result = tool_func(**arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}"
            }
    
    def _pydantic_to_json_schema(self, model_class) -> Dict[str, Any]:
        """Convert Pydantic model to JSON Schema for OpenAI structured output."""
        schema = model_class.model_json_schema()
        # OpenAI structured output expects the schema directly from Pydantic
        # but we need to ensure it's in the right format
        # Remove Pydantic-specific fields that OpenAI doesn't need
        cleaned_schema = {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
        }
        if "required" in schema and schema["required"]:
            cleaned_schema["required"] = schema["required"]
        return cleaned_schema
    
    def query(self, question: str) -> FinalAnswer:
        """Execute a query with tool calling and return structured answer."""
        self.conversation_history = []
        
        # Initialize with user question
        self.conversation_history.append({
            "role": "user",
            "content": question
        })
        
        tools = self._format_tools_for_openai()
        
        # Iterate up to max_iterations
        for iteration in range(self.max_iterations):
            is_final_round = (iteration == self.max_iterations - 1)
            system_prompt = self._get_system_prompt(is_final_round=is_final_round)
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history)
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
            }
            
            # On final round, enforce structured output
            if is_final_round:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "final_answer",
                        "strict": True,
                        "schema": self._pydantic_to_json_schema(FinalAnswer)
                    }
                }
                api_params["response_format"] = response_format
            
            # If not final round, provide tools
            if not is_final_round:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"
            
            # Make API call
            try:
                response = self.client.chat.completions.create(**api_params)
            except Exception as e:
                raise RuntimeError(f"OpenAI API call failed: {str(e)}")
            
            assistant_message = response.choices[0].message
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (assistant_message.tool_calls or [])
                ]
            })
            
            # Check if we have tool calls
            if assistant_message.tool_calls and not is_final_round:
                # Execute tools
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({"error": f"Invalid JSON arguments: {str(e)}"}, ensure_ascii=False)
                        })
                        continue
                    
                    # Execute tool
                    result = self._execute_tool(tool_name, arguments)
                    
                    # Format result for OpenAI
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # Add tool results to conversation
                self.conversation_history.extend(tool_results)
                
                # Continue to next iteration
                continue
            
            # If no tool calls or final round, we should have a final answer
            if is_final_round:
                # Parse structured output
                if assistant_message.content:
                    try:
                        # Try to parse as JSON
                        answer_data = json.loads(assistant_message.content)
                        return FinalAnswer(**answer_data)
                    except json.JSONDecodeError:
                        # If not JSON, try to extract from content
                        # This is a fallback - should not happen with structured output
                        return FinalAnswer(
                            answer=assistant_message.content or "No answer provided",
                            confidence="medium",
                            sources=[],
                            reasoning="Structured output parsing failed, using raw content"
                        )
                    except ValidationError as e:
                        raise RuntimeError(f"Failed to validate structured output: {str(e)}")
                else:
                    raise RuntimeError("No content in final response")
            else:
                # No tool calls but not final round - agent decided to answer early
                # This shouldn't happen often, but we'll handle it
                if assistant_message.content:
                    return FinalAnswer(
                        answer=assistant_message.content,
                        confidence="high",
                        sources=[],
                        reasoning="Agent provided answer without using tools"
                    )
        
        # Should not reach here, but just in case
        raise RuntimeError("Max iterations reached without final answer")

