"""Agent implementation with tool calling and structured output."""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import ValidationError

from models import FinalAnswer
from tools import TOOLS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


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
        base_prompt = """你是一个顶级的软件工程师和代码库专家。你的任务是回答关于代码库的问题。

你可以使用以下工具来帮助你探索代码库：

1. search(question: str, index_type: str, top_k: int = 5): 使用语义搜索查找相关代码
   - question: 自然语言查询，描述你要找的代码
   - index_type: 'file' 用于文件级别的概览，'function' 用于函数级别的实现细节
   - top_k: 返回结果数量（默认5）
   例如: search(question="用户登录逻辑", index_type="function", top_k=3)

2. list_file_content(file_path: str): 查看文件的完整内容
   当你从 search 工具的结果中得知一个重要文件的路径，并想查看它的完整内容时使用。
   例如: list_file_content(file_path="src/auth/service.py")

3. cat(file_path: str): 从文件系统读取文件内容（备用）
   例如: cat(file_path="src/main.py")

4. ls(dir_path: str): 列出目录中的文件和子目录
   例如: ls(dir_path="src")

5. find(pattern: str, start_path: str): 根据文件名模式查找文件
   例如: find(pattern="*.py", start_path="src")

请遵循 "思考 -> 行动 -> 观察 -> 思考..." 的循环来解决问题。优先使用 search 工具进行语义搜索。"""
        
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
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        tool_func = TOOLS[tool_name]["function"]
        try:
            logger.debug(f"Calling {tool_name} with args: {arguments}")
            result = tool_func(**arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}"
            }
    
    def _pydantic_to_json_schema(self, model_class) -> Dict[str, Any]:
        """Convert Pydantic model to JSON Schema for OpenAI structured output."""
        schema = model_class.model_json_schema()
        
        # OpenAI structured output with strict=True requires:
        # 1. additionalProperties: false
        # 2. All properties must be in required array (even optional ones)
        properties = schema.get("properties", {})
        
        # Get all property names
        all_property_names = list(properties.keys())
        
        cleaned_schema = {
            "type": schema.get("type", "object"),
            "properties": properties,
            "additionalProperties": False,  # Required by OpenAI
            "required": all_property_names,  # OpenAI strict mode requires all properties
        }
        
        # Recursively add additionalProperties: false to nested objects
        def add_additional_properties_false(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "object" and "additionalProperties" not in obj:
                    obj["additionalProperties"] = False
                # Also handle nested required arrays
                if "properties" in obj and "required" not in obj:
                    obj["required"] = list(obj["properties"].keys())
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        add_additional_properties_false(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        add_additional_properties_false(item)
        
        add_additional_properties_false(cleaned_schema)
        return cleaned_schema
    
    def query(self, question: str) -> FinalAnswer:
        """Execute a query with tool calling and return structured answer."""
        logger.info(f"🚀 Starting query: {question}")
        self.conversation_history = []
        
        # Initialize with user question
        self.conversation_history.append({
            "role": "user",
            "content": question
        })
        logger.info(f"📝 Added user question to conversation history")
        
        tools = self._format_tools_for_openai()
        logger.info(f"🔧 Available tools: {list(TOOLS.keys())}")
        
        # Iterate up to max_iterations
        for iteration in range(self.max_iterations):
            is_final_round = (iteration == self.max_iterations - 1)
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 Iteration {iteration + 1}/{self.max_iterations} {'(FINAL ROUND)' if is_final_round else ''}")
            logger.info(f"{'='*60}")
            
            system_prompt = self._get_system_prompt(is_final_round=is_final_round)
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history)
            logger.info(f"📨 Prepared {len(messages)} messages for API call")
            
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
                logger.info("🔒 Enforcing structured output (final round)")
            else:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"
                logger.info("🛠️  Tools enabled for this round")
            
            # Make API call
            logger.info(f"📡 Calling OpenAI API with model: {self.model}")
            try:
                response = self.client.chat.completions.create(**api_params)
                logger.info("✅ API call successful")
            except Exception as e:
                logger.error(f"❌ API call failed: {str(e)}")
                raise RuntimeError(f"OpenAI API call failed: {str(e)}")
            
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []
            
            logger.info(f"💬 Assistant response:")
            if assistant_message.content:
                logger.info(f"   Content: {assistant_message.content[:200]}...")
            if tool_calls:
                logger.info(f"   Tool calls: {len(tool_calls)}")
                for tc in tool_calls:
                    logger.info(f"      - {tc.function.name}({tc.function.arguments})")
            
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
                    for tc in tool_calls
                ]
            })
            
            # Check if we have tool calls
            if tool_calls and not is_final_round:
                logger.info(f"🔨 Executing {len(tool_calls)} tool call(s)...")
                # Execute tools
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    logger.info(f"   🔧 Executing tool: {tool_name}")
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        logger.info(f"      Arguments: {arguments}")
                    except json.JSONDecodeError as e:
                        logger.error(f"      ❌ Failed to parse JSON arguments: {str(e)}")
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({"error": f"Invalid JSON arguments: {str(e)}"}, ensure_ascii=False)
                        })
                        continue
                    
                    # Execute tool
                    result = self._execute_tool(tool_name, arguments)
                    logger.info(f"      ✅ Tool execution result: success={result.get('success', False)}")
                    if result.get("success"):
                        if "items" in result:
                            logger.info(f"         Found {len(result.get('items', []))} items")
                        elif "files" in result:
                            logger.info(f"         Found {len(result.get('files', []))} files")
                        elif "content" in result:
                            content_len = len(result.get('content', ''))
                            logger.info(f"         Content length: {content_len} chars")
                    else:
                        logger.warning(f"         Error: {result.get('error', 'Unknown error')}")
                    
                    # Format result for OpenAI
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # Add tool results to conversation
                self.conversation_history.extend(tool_results)
                logger.info(f"📝 Added {len(tool_results)} tool result(s) to conversation history")
                
                # Continue to next iteration
                continue
            
            # If no tool calls or final round, we should have a final answer
            if is_final_round:
                logger.info("🎯 Final round - parsing structured output...")
                # Parse structured output
                if assistant_message.content:
                    try:
                        # Try to parse as JSON
                        logger.info("   Parsing JSON response...")
                        answer_data = json.loads(assistant_message.content)
                        logger.info(f"   ✅ Parsed JSON successfully")
                        logger.info(f"   Validating with Pydantic model...")
                        final_answer = FinalAnswer(**answer_data)
                        logger.info(f"   ✅ Validation successful")
                        logger.info(f"   Answer: {final_answer.answer[:100]}...")
                        logger.info(f"   Confidence: {final_answer.confidence}")
                        logger.info(f"   Sources: {final_answer.sources}")
                        return final_answer
                    except json.JSONDecodeError as e:
                        logger.warning(f"   ⚠️  JSON parsing failed: {str(e)}")
                        logger.info("   Using fallback: raw content")
                        # If not JSON, try to extract from content
                        # This is a fallback - should not happen with structured output
                        return FinalAnswer(
                            answer=assistant_message.content or "No answer provided",
                            confidence="medium",
                            sources=[],
                            reasoning="Structured output parsing failed, using raw content"
                        )
                    except ValidationError as e:
                        logger.error(f"   ❌ Pydantic validation failed: {str(e)}")
                        raise RuntimeError(f"Failed to validate structured output: {str(e)}")
                else:
                    logger.error("   ❌ No content in final response")
                    raise RuntimeError("No content in final response")
            else:
                # No tool calls but not final round - agent decided to answer early
                logger.info("💡 Agent provided answer without using tools (early exit)")
                if assistant_message.content:
                    return FinalAnswer(
                        answer=assistant_message.content,
                        confidence="high",
                        sources=[],
                        reasoning="Agent provided answer without using tools"
                    )
        
        # Should not reach here, but just in case
        logger.error("❌ Max iterations reached without final answer")
        raise RuntimeError("Max iterations reached without final answer")

