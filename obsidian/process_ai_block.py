from ai_core import AI, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from ai_core.types import Message, MessageContent, ToolCall, ToolResult
from ai_core.tools import Tool
from ai_core.models import DEFAULT_MODEL_IDENTIFIER

from typing import Dict, List
from obsidian.beacons import beacon_me, beacon_ai, beacon_error, beacon_tokens_prefix
from obsidian.process_conversation import process_conversation
import os
from obsidian.parser.tag_parser import process_tags
from ui.tool_confirmation import confirm_tool_execution
from config.paths import PATHS
import json
import traceback
from config.logging_config import setup_logger
from obsidian.beacons import beacon_tool_start, beacon_tool_end
from toolsets import TOOL_SETS
from obsidian.context_pulling import insert_file_ref, fetch_url_content
import subprocess
from obsidian.notification_utils import play_notification_sound, play_error_sound

logger = setup_logger(__name__)

# Constants
PROMPT_MOD = "You will be passed a document and some instructions to modify this document. Please reply strictly with the text of the new document (no surrounding xml, no narration).\n"

# New constants
beacon_thought = "|THOUGHT|"
beacon_end_thought = "|/THOUGHT|"

# Initialize AI model
model = AI("haiku")

# Define replacement functions
remove = lambda *_: ""

def calculate_cumulative_tokens(conversation_text: str, system_prompt: str = None) -> tuple[int, int]:
    """
    Calculate cumulative input/output tokens from conversation text.
    Returns (input_tokens, output_tokens) based on character count / 4.
    
    Input tokens include: user messages, system prompts, tool call arguments, tool results
    Output tokens include: AI responses, thought blocks
    """
    input_chars = 0
    output_chars = 0
    
    # Count system prompt if provided
    if system_prompt:
        input_chars += len(system_prompt)
    
    # Split by AI beacon to process sections
    sections = conversation_text.split(beacon_ai)
    
    # First section is always user input (before first AI response)
    if sections[0].strip():
        # Remove any reply tags or other metadata
        user_text = sections[0].strip()
        input_chars += len(user_text)
    
    # Process subsequent sections
    for section in sections[1:]:
        # Skip token beacons themselves
        if beacon_tokens_prefix in section:
            # Extract the part after token beacon
            token_end = section.find("|==")
            if token_end > -1:
                section = section[token_end + 3:]
        
        # Split by ME beacon to separate AI response from next user input  
        parts = section.split(beacon_me)
        
        # First part is AI response (may include thought blocks and tool calls)
        if parts[0]:
            ai_part = parts[0]
            
            # Extract and count thought blocks
            thought_start = ai_part.find(beacon_thought)
            while thought_start != -1:
                thought_end = ai_part.find(beacon_end_thought, thought_start)
                if thought_end != -1:
                    thought_content = ai_part[thought_start + len(beacon_thought):thought_end]
                    output_chars += len(thought_content)
                    # Remove the thought block from ai_part
                    ai_part = ai_part[:thought_start] + ai_part[thought_end + len(beacon_end_thought):]
                else:
                    break
                thought_start = ai_part.find(beacon_thought)
            
            # Extract and count tool calls and results
            tool_start = ai_part.find(beacon_tool_start)
            while tool_start != -1:
                tool_end = ai_part.find(beacon_tool_end, tool_start)
                if tool_end != -1:
                    tool_section = ai_part[tool_start:tool_end + len(beacon_tool_end)]
                    
                    # Parse tool section to separate call from result
                    if "Arguments:" in tool_section and "Result:" in tool_section:
                        args_start = tool_section.find("Arguments:") + len("Arguments:")
                        result_start = tool_section.find("Result:")
                        
                        # Tool arguments count as input
                        args_section = tool_section[args_start:result_start].strip()
                        input_chars += len(args_section)
                        
                        # Tool results count as input
                        result_section = tool_section[result_start + len("Result:"):].strip()
                        input_chars += len(result_section)
                    
                    # Remove the tool section from ai_part
                    ai_part = ai_part[:tool_start] + ai_part[tool_end + len(beacon_tool_end):]
                else:
                    break
                tool_start = ai_part.find(beacon_tool_start)
            
            # Remaining AI text counts as output
            output_chars += len(ai_part.strip())
        
        # Second part (if exists) is user input
        if len(parts) > 1 and parts[1].strip():
            input_chars += len(parts[1].strip())
    
    # Convert to tokens (divide by 4 and round)
    input_tokens = round(input_chars / 4)
    output_tokens = round(output_chars / 4)
    
    return input_tokens, output_tokens

def calculate_tokens_from_messages(messages: List[Message], system_prompt: str = None) -> tuple[int, int]:
    """
    Calculate cumulative input/output tokens from Message objects.
    This gives the accurate count of what's actually sent to the AI.
    Returns (input_tokens, output_tokens) based on character count / 4.
    
    Input tokens include: user messages, system prompts, tool call arguments, tool results
    Output tokens include: AI responses
    """
    input_chars = 0
    output_chars = 0
    
    # Count system prompt if provided
    if system_prompt:
        input_chars += len(system_prompt)
    
    # Process each message
    for message in messages:
        if message.role == "user":
            # User messages count as input
            for content in message.content:
                if content.type == "text" and content.text:
                    input_chars += len(content.text)
                elif content.type == "tool_result" and content.tool_result:
                    # Tool results count as input
                    if content.tool_result.result:
                        input_chars += len(str(content.tool_result.result))
                    if content.tool_result.error:
                        input_chars += len(str(content.tool_result.error))
                # Note: Images are not counted for now as requested
                    
        elif message.role == "assistant":
            # Assistant messages count as output
            for content in message.content:
                if content.type == "text" and content.text:
                    output_chars += len(content.text)
                elif content.type == "tool_use" and content.tool_call:
                    # Tool call arguments count as input (they're sent to the tool, not output to user)
                    if content.tool_call.arguments:
                        input_chars += len(json.dumps(content.tool_call.arguments))
    
    # Convert to tokens (divide by 4 and round)
    input_tokens = round(input_chars / 4)
    output_tokens = round(output_chars / 4)
    
    return input_tokens, output_tokens

def calculate_tokens_including_current_response(messages: List[Message], current_response: str, system_prompt: str = None) -> tuple[int, int]:
    """
    Calculate tokens including the current AI response that hasn't been added to messages yet.
    
    Args:
        messages: List of Message objects from the conversation
        current_response: The current AI response text that will be added
        system_prompt: Optional system prompt
        
    Returns:
        (input_tokens, output_tokens) tuple
    """
    # First get the base counts from existing messages
    input_tokens, output_tokens = calculate_tokens_from_messages(messages, system_prompt)
    
    # Add the current response to output tokens
    if current_response:
        output_tokens += round(len(current_response) / 4)
    
    return input_tokens, output_tokens

REPLACEMENTS_OUTSIDE = {
    "help": lambda *_: """# Obsidian AI Help

> [!warning] About the examples below
> All tag examples in this help use **UPPERCASE** (e.g., `<AI!>`, `<REPLY!>`) to prevent them from being processed when you view this help. When you write your own tags, **use lowercase**: `<ai!>`, `<reply!>`, `<model!>`, etc.

## Basic Usage

Add an AI block to any note, include `<REPLY!>` where you want the response:

```
<AI!>
What are the key points in this note?
<REPLY!>
</AI!>
```

Save the file, and the AI will respond where `<REPLY!>` was placed.

## AI Model & Parameters

- `<MODEL!name>` - Choose model: haiku (default), sonnet, opus, gpt4, gemini, etc.
- `<TEMPERATURE!0.7>` - Set randomness (0.0-1.0)
- `<MAX_TOKENS!4000>` - Set max response length
- `<SYSTEM!prompt_name>` - Use a prompt from your vault's Prompts folder
- `<THINK!>` - Enable extended thinking mode
- `<DEBUG!>` - Show debug info

## Content References

- `<THIS!>` - Include the current document
- `<DOC!path>` or `<DOC![[Note Name]]>` - Include another document
- `<FILE!path>` - Include any file
- `<PDF!path>` - Include a PDF (extracts text)
- `<PROMPT!name>` - Include a prompt from Prompts folder
- `<URL!https://...>` - Fetch and include webpage content
- `<IMAGE!path>` - Include an image for vision models

## Tools

Enable AI tools with `<TOOLS!toolset>`:

- `system` - File operations, run commands, execute Python
- `obsidian` - Read vault notes and structure
- `gmail` - Send/read emails
- `discord` - Discord messaging
- `subagents` - Create sub-AI agents

Example with tools:
```
<AI!>
<TOOLS!gmail>
<TOOLS!system>
Search my emails for invoices from last month and save a summary.
<REPLY!>
</AI!>
```

## Tag Formats

Tags support multiple formats (shown uppercase here, use lowercase when writing):
- `<NAME!value>` - Self-closing with value
- `<NAME!>content</NAME!>` - With content block
- `<NAME![[Wiki Link]]>` - Obsidian wiki links
- `<NAME!"quoted value">` - Quoted values for spaces

## Examples

**Simple question:**
```
<AI!>
Summarize this note in 3 bullet points.
<REPLY!>
</AI!>
```

**With a custom model and system prompt:**
```
<AI!>
<MODEL!opus>
<SYSTEM!code_reviewer>
Review this code for potential issues.
<REPLY!>
</AI!>
```

**Analyzing an image:**
```
<AI!>
<MODEL!sonnet>
<IMAGE!Screenshots/diagram.png>
Explain what this diagram shows.
<REPLY!>
</AI!>
```

**Using tools:**
```
<AI!>
<TOOLS!obsidian>
List all notes in my Projects folder that mention "deadline".
<REPLY!>
</AI!>
```
""",
    "ai": lambda value, text, context: process_ai_block(text, context, value),
    "script": lambda value, text, context: run_python_script(value, text, context),
}

REPLACEMENTS_INSIDE = {
    "reply": remove,
    "back": remove,
    "model": remove,
    "system": remove,
    "debug": remove,
    "temperature": remove,
    "max_tokens": remove,
    "mock": remove,
    "tools": remove,
    "think": remove,
    "this": lambda v, t, context: f"<document>{context}</document>\n",
    "doc": lambda v, t, c: insert_file_ref(v),
    "pdf": lambda v, t, c: insert_file_ref(v, "pdf", typ="pdf"),
    "file": lambda v, t, c: insert_file_ref(v),
    "prompt": lambda v, t, c: insert_file_ref(v, "Prompts", "prompt"),
    "url": lambda v, t, c: f"<url>{v}</url>\n<content>{fetch_url_content(v)}</content>\n",
}

def process_ai_block(block: str, context: Dict, option: str) -> str:
    """
    Process an AI block in the document.

    Args:
        block (str): Content of the AI block
        context (Dict): Context information including file_path
        option (str): Processing option (None, "rep", or "all")

    Returns:
        str: Processed AI block
    """
    option_txt = option or ""
    _, results = process_tags(block)
    if "reply" not in set([n for n,v,t in results]):
        return f"<ai!{option_txt}>{block}</ai!>"
    initial_block = block
    block, results = process_tags(block, {"reply": remove})

    try:
        # Add immediate feedback that AI is processing
        current_content = update_file_content(
            initial_block,
            f"{beacon_ai}\n_Thinking..._\n",
            context["file_path"]
        )

        conv_txt = block.strip()
        conv_txt, results = process_tags(conv_txt, REPLACEMENTS_INSIDE, context=context["doc"])
        params = dict([(n, v) for n, v, t in results])

        model_identifier = params.get("model", DEFAULT_MODEL_IDENTIFIER)
        system_prompt = params.get("system")
        debug = ("debug" in params)
        temperature = float(params.get("temperature", DEFAULT_TEMPERATURE))
        max_tokens = int(params.get("max_tokens", DEFAULT_MAX_TOKENS))
        tools_keys = [v for n, v, t in results if n == "tools" and v]
        tools = merge_tools(tools_keys)
        # Check if thinking mode is enabled
        thinking = "think" in params
        thinking_budget_tokens = None
        if thinking and params.get("think"):
            try:
                thinking_budget_tokens = int(params.get("think"))
            except ValueError:
                logger.warning("Invalid thinking budget: %s. Using default.", params.get("think"))
        
        if "mock" in params:
            model_identifier = "mock"

        if debug:
            logger.debug("---PARAMETERS START---")
            for name, value in params.items():
                logger.debug("%s: %s", name, value)
            logger.debug("---PARAMETERS END---")
            logger.debug("---CONVERTED TEXT START---")
            logger.debug("%s", conv_txt.encode("utf-8"))
            logger.debug("---CONVERTED TEXT END---")
            if thinking:
                logger.debug("Thinking mode enabled. Budget: %s", thinking_budget_tokens or "default")

        logger.info("Answering with %s...", model_identifier)
        if option != "all":
            messages = process_conversation(conv_txt)
        else:
            messages = process_conversation(f"{PROMPT_MOD}<document>{context['doc']}</document><instructions>{conv_txt}</instructions>")

        if system_prompt is not None:
            # Load system prompt from the vault's Prompts folder
            prompt_path = os.path.join(PATHS.prompts_library, f"{system_prompt}.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read()
            else:
                raise FileNotFoundError(f"Could not find system prompt '{system_prompt}' in {PATHS.prompts_library}")
        
        ai_response = model.messages(messages, system_prompt=system_prompt, model_override=model_identifier,
                                    max_tokens=max_tokens, temperature=temperature,
                                    tools=tools, thinking=thinking, thinking_budget_tokens=thinking_budget_tokens)
        response = ""
        thoughts = ""
        
        # Track reasoning output separately for token counting  
        total_reasoning_chars = 0
        
        start = True
        while True:  # Process responses until no more tool calls
            response += ai_response.content

            if ai_response.content.strip():
                escaped_response = escape_response(ai_response.content)
                
                # For the first response, add the AI beacon
                if start:
                    # Add just the AI beacon first
                    current_content = update_file_content(
                        current_content,
                        f"{beacon_ai}\n",
                        context["file_path"]
                    )
                    start = False
                
                # Add the AI response
                current_content = update_file_content(
                    current_content,
                    f"{escaped_response}\n",
                    context["file_path"]
                )
                if ai_response.reasoning and ai_response.reasoning.strip():
                    logger.debug("Reasoning: %s", ai_response.reasoning[:100])
                    escaped_reasoning = escape_response(ai_response.reasoning)
                    thought_block = f"\n{beacon_thought}\n{escaped_reasoning}\n{beacon_end_thought}\n"
                    thoughts += thought_block
                    # Count reasoning as additional output
                    total_reasoning_chars += len(ai_response.reasoning)
                    current_content = update_file_content(current_content, thought_block, context["file_path"])

            if not ai_response.tool_calls:
                break  # No (more) tool calls, we're done

            # Process all tool calls at once
            tool_results = []
            for tool_call in ai_response.tool_calls:
                tool_call_text = format_tool_call(tool_call)
                current_content = update_file_content(
                    current_content,
                    tool_call_text,
                    context["file_path"]
                )
                try:
                    # Find the matching tool from provided tools
                    tool = next(t for t in tools if t.tool.name == tool_call.name)
                    
                    # Check if tool needs confirmation
                    if not tool.tool.safe:
                        confirmed, user_message = confirm_tool_execution(tool.tool, tool_call.arguments)
                        if not confirmed:
                            # User rejected the tool execution
                            error_msg = "Tool execution rejected by user"
                            if user_message:
                                error_msg += f"\nUser message: {user_message}"
                            tool_result = ToolResult(
                                name=tool_call.name,
                                result=None,
                                tool_call_id=tool_call.id,
                                error=error_msg
                            )
                            tool_results.append(tool_result)
                            tool_result_text = format_tool_result(tool_result)
                            current_content = update_file_content(
                                current_content,
                                tool_result_text,
                                context["file_path"]
                            )
                            continue
                    
                    # Execute the tool
                    result = tool.tool.func(**tool_call.arguments)
                    # Format the result
                    tool_result = ToolResult(
                        name=tool_call.name,
                        result=result,
                        tool_call_id=tool_call.id
                    )
                    tool_results.append(tool_result)
                    tool_result_text = format_tool_result(tool_result)
                    current_content = update_file_content(
                        current_content,
                        tool_result_text,
                        context["file_path"]
                    )
                except Exception as e:
                    tool_result = ToolResult(
                        name=tool_call.name,
                        result=None,
                        tool_call_id=tool_call.id,
                        error=f"{str(e)}\n{traceback.format_exc()}"
                    )
                    tool_results.append(tool_result)
                    tool_result_text = format_tool_result(tool_result)
                    current_content = update_file_content(
                        current_content,
                        tool_result_text,
                        context["file_path"]
                    )
            
            # Add tool calls and results to response text
            for tool_call, tool_result in zip(ai_response.tool_calls, tool_results):
                response += "\n" + format_tool_call(tool_call)
                response += format_tool_result(tool_result)
            
            # Add tool call and result to messages for context
            assistant_content = []
            if ai_response.content.strip():  # Only add text content if non-empty
                assistant_content.append(MessageContent(
                    type="text",
                    text=ai_response.content
                ))
            # Add tool calls
            assistant_content.extend([
                MessageContent(
                    type="tool_use",
                    tool_call=tool_call
                ) for tool_call in ai_response.tool_calls
            ])
            
            messages.append(Message(
                role="assistant",
                content=assistant_content
            ))

            # Add all tool results in a single user message
            messages.append(Message(
                role="user",
                content=[MessageContent(
                    type="tool_result",
                    tool_result=result
                ) for result in tool_results]
            ))
            
            # Get AI's response to tool results
            ai_response = model.messages(messages, system_prompt=system_prompt, model_override=model_identifier,
                                    max_tokens=max_tokens, temperature=temperature,
                                    tools=tools, thinking=thinking, thinking_budget_tokens=thinking_budget_tokens)

        # Calculate tokens before escaping (for accurate count)
        if option is None:
            # Calculate final cumulative tokens for the entire conversation
            # Note: 'response' contains the accumulated response text that hasn't been added to messages
            final_input_tokens, final_output_tokens = calculate_tokens_including_current_response(
                messages, response, system_prompt  # Use unescaped response
            )
            
            # Add the additional AI output (reasoning) that's not in messages
            final_output_tokens += round(total_reasoning_chars / 4)
            
            # Debug logging
            if debug:
                logger.debug("=== TOKEN COUNTING DEBUG ===")
                logger.debug(f"Number of messages: {len(messages)}")
                for i, msg in enumerate(messages):
                    if msg.role == "assistant":
                        total_chars = sum(len(c.text) for c in msg.content if c.type == "text" and c.text)
                        logger.debug(f"Message {i}: Assistant message with {len(msg.content)} content items, {total_chars} text chars")
                        for j, c in enumerate(msg.content):
                            if c.type == "text" and c.text:
                                logger.debug(f"  Content {j}: {len(c.text)} chars, preview: {c.text[:50]}...")
                    elif msg.role == "user":
                        total_chars = sum(len(c.text) for c in msg.content if c.type == "text" and c.text)
                        logger.debug(f"Message {i}: User message with {len(msg.content)} content items, {total_chars} text chars")
                
                # Log the accumulated response
                logger.debug(f"Accumulated 'response' variable: {len(response)} chars")
                logger.debug(f"Response preview: {response[:100]}...")
                
                logger.debug(f"Total reasoning chars: {total_reasoning_chars}")
                logger.debug(f"Base output tokens from messages: {final_output_tokens - round(total_reasoning_chars / 4) - round(len(response) / 4)}")
                logger.debug(f"Current response tokens: {round(len(response) / 4)}")
                logger.debug(f"Reasoning tokens: {round(total_reasoning_chars / 4)}")
                logger.debug(f"Final output tokens: {final_output_tokens}")
                logger.debug("=== END TOKEN DEBUG ===")

        # Now escape the response for display
        response = escape_response(response)
        if option is None:
            final_token_beacon = f"{beacon_tokens_prefix}In={final_input_tokens},Out={final_output_tokens}|==\n"
            new_block = f"{block}{beacon_ai}\n{final_token_beacon}{thoughts}\n{response}\n{beacon_me}\n"
        elif option == "rep":
            play_notification_sound()  # Play sound on successful completion
            return response
        elif option == "all":
            context["new_doc"] = response
            play_notification_sound()  # Play sound on successful completion
            return response
    except Exception:
        new_block = f"{block}{beacon_error}\n```sh\n{traceback.format_exc()}```\n"
        play_error_sound()  # Play sound even on error to notify completion
    
    # Play notification sound when normal processing completes
    play_notification_sound()
    return f"<ai!{option_txt}>{new_block}</ai!>"

def format_tool_call(tool_call: ToolCall) -> str:
    """Format a tool call into a parseable string"""
    return (
        f"{beacon_tool_start}\n"
        f"ID: {tool_call.id}\n"
        f"Tool: {tool_call.name}\n"
        f"Arguments:\n"
        f"```json\n"
        f"{json.dumps(tool_call.arguments, indent=2)}\n"
        f"```\n"
    )

def format_tool_result(result: ToolResult) -> str:
    """Format a tool result into a parseable string"""
    return (
        f"Result:\n"
        f"```json\n"
        f"{json.dumps({'result': result.result, 'error': result.error}, indent=2)}\n"
        f"```\n"
        f"{beacon_tool_end}\n"
    )

def escape_response(response: str) -> str:
    """
    Escape special keywords in the AI's response.

    Args:
        response (str): AI's response

    Returns:
        str: Escaped response
    """
    def create_replacement_func(key):
        def func(v, t, c):
            mod_key = key.upper()
            v = v or ""
            if t is None:
                return f"<{mod_key}!{v}>"
            else:
                return f"<{mod_key}!{v}>{t}</{mod_key}!>"
        return func
    
    replacements = {}
    names = list(REPLACEMENTS_OUTSIDE.keys()) + list(REPLACEMENTS_INSIDE.keys())
    for k in names:
        replacements[k] = create_replacement_func(k)
    new_response, _ = process_tags(response, replacements)
    return new_response

def get_tools_from_key(key: str) -> List[Tool]:
    """Get tools from a predefined key"""
    return TOOL_SETS.get(key, [])

def merge_tools(tools_keys: List[str]) -> List[Tool]:
    """Merge multiple toolsets together"""
    all_tools = []
    for key in tools_keys:
        tools = get_tools_from_key(key)
        if tools:
            all_tools.extend(tools)
    return all_tools

def update_file_content(current_content: str, new_text: str, file_path: str) -> str:
    """
    Update the file by finding the current content and appending new text to it.
    
    Args:
        current_content (str): Current content to find in the file
        new_text (str): New text to append
        file_path (str): Path to the file to update
    
    Returns:
        str: Updated current_content
    """
    # Update current content with new text
    updated_content = f"{current_content}{new_text}"
    
    # Read the full file
    with open(file_path, "r", encoding="utf-8") as f:
        full_content = f.read()
    
    # Replace the exact current content with updated content
    full_content = full_content.replace(current_content, updated_content)
    
    # Write the updated content back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    os.utime(file_path, None) # necessary to trigger Obsidian to reload the file

    return updated_content

def run_python_script(script_name: str, text: str, context: Dict) -> str:
    """
    Run a Python script and return its output.
    
    If script_name has .md extension or no extension, it's treated as a markdown file,
    and the first Python code block is executed.
    
    Args:
        script_name (str): Name of the script file to run
        text (str): Content of the script block (not used)
        context (Dict): Context information
        
    Returns:
        str: Output from the script execution
    """
    import sys
    try:
        # Check if script name is a markdown file (has .md extension or no extension)
        is_markdown = script_name.endswith('.md') or '.' not in script_name
        
        # Add .md extension if not present but is markdown
        if is_markdown and not script_name.endswith('.md'):
            script_name = f"{script_name}.md"
        
        # Find script in the scripts folder
        script_path = os.path.join(PATHS.scripts_folder, script_name)
        
        if not os.path.exists(script_path):
            return f"Error: Script '{script_name}' not found in scripts folder: {PATHS.scripts_folder}"
        
        if is_markdown:
            # Extract Python code from markdown file
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the first Python code block
            import re
            pattern = r'```python\s*\n(.*?)```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            if not matches:
                return f"Error: No Python code block found in '{script_name}'"
            
            # Extract the first Python code block
            code = matches[0]
            
            # Execute the python code directly using subprocess with -c
            # Use sys.executable to ensure we use the same Python interpreter
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(PATHS.scripts_folder)  # Set working directory to scripts folder
            )
            
            return result.stdout
        else:
            # Direct execution of Python script
            # Use sys.executable to ensure we use the same Python interpreter
            result = subprocess.run(
                [sys.executable, script_path], 
                capture_output=True,
                text=True,
                check=True,
                cwd=str(PATHS.scripts_folder)  # Set working directory to scripts folder
            )
            
            # Return the stdout output
            return result.stdout
        
    except subprocess.CalledProcessError as e:
        return f"Error executing script '{script_name}':\nstdout: {e.stdout}\nstderr: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}\n{traceback.format_exc()}"