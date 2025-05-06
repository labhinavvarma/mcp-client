import streamlit as st
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.sse import sse_client
import json
import yaml

# Page configuration
st.set_page_config(page_title="MCP Healthcare Chatbot", page_icon="🏥", layout="wide")

# App title
st.title("Healthcare AI Assistant")
st.markdown("Connect to MCP server and chat with healthcare AI models")

# Initialize session states
if "messages" not in st.session_state:
    st.session_state.messages = []
if "server_info" not in st.session_state:
    st.session_state.server_info = {
        "resources": [],
        "tools": [],
        "prompts": [],
        "yaml_content": "",
        "search_objects": []
    }
if "server_connected" not in st.session_state:
    st.session_state.server_connected = False

# Server connection sidebar
with st.sidebar:
    st.header("Server Connection")
    server_url = st.text_input("Server URL", value="http://10.126.192.183:8000/sse", 
                              help="The URL of your MCP server")
    server_transport = "sse"
    
    # Connect button
    if st.button("Connect to Server"):
        with st.spinner("Connecting to MCP server..."):
            # Function to fetch server information
            async def fetch_server_info(url):
                try:
                    # Use direct MCP connection like in the reference code
                    async with sse_client(url=url) as sse_connection:
                        async with ClientSession(*sse_connection) as session:
                            await session.initialize()
                            
                            # Get resources
                            resources_list = []
                            resources = await session.list_resources()
                            if hasattr(resources, 'resources') and resources.resources:
                                for resource in resources.resources:
                                    resource_info = {
                                        "name": resource.name,
                                        "description": resource.description if hasattr(resource, 'description') else "No description"
                                    }
                                    
                                    # Check for parametric resources
                                    if '{' in resource.name:
                                        params = []
                                        current_pos = 0
                                        while True:
                                            param_start = resource.name.find('{', current_pos)
                                            if param_start == -1:
                                                break
                                            param_end = resource.name.find('}', param_start)
                                            if param_end == -1:
                                                break
                                            param_name = resource.name[param_start+1:param_end]
                                            params.append(param_name)
                                            current_pos = param_end + 1
                                        resource_info["parameters"] = params
                                    
                                    resources_list.append(resource_info)
                            
                            # Get tools
                            tools_list = []
                            tools = await session.list_tools()
                            if hasattr(tools, 'tools') and tools.tools:
                                seen_tools = set()
                                for tool in tools.tools:
                                    if tool.name not in seen_tools:
                                        seen_tools.add(tool.name)
                                        tools_list.append({
                                            "name": tool.name,
                                            "description": tool.description if hasattr(tool, 'description') and tool.description else "No description"
                                        })
                            
                            # Get prompts
                            prompts_list = []
                            try:
                                prompts = await session.list_prompts()
                                if hasattr(prompts, 'prompts') and prompts.prompts:
                                    seen_prompts = set()
                                    for prompt in prompts.prompts:
                                        if prompt.name not in seen_prompts:
                                            seen_prompts.add(prompt.name)
                                            prompt_info = {
                                                "name": prompt.name,
                                                "description": prompt.description if hasattr(prompt, 'description') and prompt.description else "No description"
                                            }
                                            
                                            # Add arguments if available
                                            if hasattr(prompt, 'arguments') and prompt.arguments:
                                                prompt_info["arguments"] = []
                                                for arg in prompt.arguments:
                                                    prompt_info["arguments"].append({
                                                        "name": arg.name,
                                                        "required": arg.required,
                                                        "description": arg.description if hasattr(arg, 'description') else ""
                                                    })
                                            
                                            prompts_list.append(prompt_info)
                            except Exception as e:
                                st.error(f"Error listing prompts: {e}")
                            
                            # Get YAML content
                            yaml_content = ""
                            try:
                                yaml_result = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                                if hasattr(yaml_result, 'contents') and yaml_result.contents:
                                    for item in yaml_result.contents:
                                        if hasattr(item, 'text'):
                                            try:
                                                parsed_yaml = yaml.safe_load(item.text)
                                                yaml_content = yaml.dump(parsed_yaml, default_flow_style=False, sort_keys=False)
                                            except yaml.YAMLError as e:
                                                yaml_content = f"Failed to parse YAML: {e}\nRaw content: {item.text}"
                            except Exception as e:
                                yaml_content = f"Error reading YAML content: {e}"
                            
                            # Get search objects
                            search_objects = []
                            try:
                                content = await session.read_resource("search://cortex_search/search_obj/list")
                                if hasattr(content, 'contents') and isinstance(content.contents, list):
                                    for item in content.contents:
                                        if hasattr(item, 'text'):
                                            objects = json.loads(item.text)
                                            search_objects = objects
                                            break
                            except Exception as e:
                                st.error(f"Error getting search objects: {e}")
                            
                            return {
                                "resources": resources_list,
                                "tools": tools_list,
                                "prompts": prompts_list,
                                "yaml_content": yaml_content,
                                "search_objects": search_objects
                            }
                except Exception as e:
                    st.error(f"Connection error: {e}")
                    return None
            
            # Run the async function to fetch server info
            server_info = asyncio.run(fetch_server_info(server_url))
            
            if server_info:
                st.session_state.server_info = server_info
                st.session_state.server_connected = True
                st.success("✅ Connected to server successfully!")
            else:
                st.error("❌ Failed to connect to server")
    
    # Only show these options if connected
    if st.session_state.server_connected:
        st.success("Connected to server")
        
        # Server information tabs
        st.header("Server Information")
        server_tabs = st.tabs(["Prompts", "Tools", "Resources", "Search Objects", "YAML Content"])
        
        # Fetch server information directly
        async def fetch_server_data():
            try:
                async with sse_client(url=server_url) as sse_connection:
                    async with ClientSession(*sse_connection) as session:
                        await session.initialize()
                        return session
            except Exception as e:
                st.error(f"Connection error: {e}")
                return None
        
        # Prompts tab
        with server_tabs[0]:
            st.subheader("Available Prompts")
            try:
                session = asyncio.run(fetch_server_data())
                if session:
                    prompts = asyncio.run(session.list_prompts())
                    if hasattr(prompts, 'prompts') and prompts.prompts:
                        seen_prompts = set()
                        for prompt in prompts.prompts:
                            if prompt.name not in seen_prompts:
                                seen_prompts.add(prompt.name)
                                with st.expander(f"📝 {prompt.name}"):
                                    st.write(f"**Description:** {prompt.description if hasattr(prompt, 'description') else 'No description'}")
                                    if hasattr(prompt, 'arguments') and prompt.arguments:
                                        st.write("**Arguments:**")
                                        for arg in prompt.arguments:
                                            required_str = "Required" if arg.required else "Optional"
                                            st.write(f"- {arg.name} [{required_str}]: {arg.description if hasattr(arg, 'description') else ''}")
                    else:
                        st.info("No prompts found on server")
            except Exception as e:
                st.error(f"Error fetching prompts: {e}")
        
        # Tools tab
        with server_tabs[1]:
            st.subheader("Available Tools")
            try:
                session = asyncio.run(fetch_server_data())
                if session:
                    tools = asyncio.run(session.list_tools())
                    if hasattr(tools, 'tools') and tools.tools:
                        seen_tools = set()
                        for tool in tools.tools:
                            if tool.name not in seen_tools:
                                seen_tools.add(tool.name)
                                with st.expander(f"🔧 {tool.name}"):
                                    st.write(f"**Description:** {tool.description if hasattr(tool, 'description') else 'No description'}")
                    else:
                        st.info("No tools found on server")
            except Exception as e:
                st.error(f"Error fetching tools: {e}")
        
        # Resources tab
        with server_tabs[2]:
            st.subheader("Available Resources")
            try:
                session = asyncio.run(fetch_server_data())
                if session:
                    resources = asyncio.run(session.list_resources())
                    if hasattr(resources, 'resources') and resources.resources:
                        for resource in resources.resources:
                            with st.expander(f"📚 {resource.name}"):
                                st.write(f"**Description:** {resource.description if hasattr(resource, 'description') else 'No description'}")
                                # Check for parametric resources
                                if '{' in resource.name:
                                    st.write("**Parameters:**")
                                    current_pos = 0
                                    while True:
                                        param_start = resource.name.find('{', current_pos)
                                        if param_start == -1:
                                            break
                                        param_end = resource.name.find('}', param_start)
                                        if param_end == -1:
                                            break
                                        param_name = resource.name[param_start+1:param_end]
                                        st.write(f"- {param_name}")
                                        current_pos = param_end + 1
                    else:
                        st.info("No resources found on server")
            except Exception as e:
                st.error(f"Error fetching resources: {e}")
        
        # Search Objects tab
        with server_tabs[3]:
            st.subheader("Search Objects")
            try:
                session = asyncio.run(fetch_server_data())
                if session:
                    try:
                        content = asyncio.run(session.read_resource("search://cortex_search/search_obj/list"))
                        if hasattr(content, 'contents') and isinstance(content.contents, list):
                            objects_found = False
                            for item in content.contents:
                                if hasattr(item, 'text'):
                                    objects = json.loads(item.text)
                                    st.json(objects)
                                    objects_found = True
                                    break
                            if not objects_found:
                                st.info("No search objects found on server")
                    except Exception as e:
                        st.error(f"Error fetching search objects: {e}")
            except Exception as e:
                st.error(f"Error connecting to server: {e}")
        
        # YAML Content tab
        with server_tabs[4]:
            st.subheader("YAML Content")
            try:
                session = asyncio.run(fetch_server_data())
                if session:
                    try:
                        yaml_result = asyncio.run(session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list"))
                        if hasattr(yaml_result, 'contents') and yaml_result.contents:
                            yaml_found = False
                            for item in yaml_result.contents:
                                if hasattr(item, 'text'):
                                    try:
                                        parsed_yaml = yaml.safe_load(item.text)
                                        formatted_yaml = yaml.dump(parsed_yaml, default_flow_style=False, sort_keys=False)
                                        st.code(formatted_yaml, language="yaml")
                                        yaml_found = True
                                        break
                                    except yaml.YAMLError as e:
                                        st.error(f"Failed to parse YAML: {e}")
                                        st.code(item.text)
                                        yaml_found = True
                                        break
                            if not yaml_found:
                                st.info("No YAML content found on server")
                    except Exception as e:
                        st.error(f"Error fetching YAML content: {e}")
            except Exception as e:
                st.error(f"Error connecting to server: {e}")

# Main chat interface
chat_col1, chat_col2 = st.columns([3, 1])

with chat_col1:
    # Prompt selection
    prompt_type = st.selectbox(
        "Select Prompt Type",
        ["Calculator", "HEDIS Expert", "Weather"]
    )
    
    prompt_map = {
        "Calculator": "calculator-prompt",
        "HEDIS Expert": "hedis-prompt",
        "Weather": "weather-prompt"
    }
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Input for the query
    query = st.chat_input("Type your query here...")
    
    # Function to process query
    async def process_query(query_text):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": query_text})
        
        # Show thinking message
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.text("Processing...")
            
            try:
                # Connect to MCP client
                async with MultiServerMCPClient(
                    {
                        "DataFlyWheelServer": {
                            "url": server_url,
                            "transport": server_transport,
                        }
                    }
                ) as client:
                    # Create a mock model for testing
                    class MockLLM:
                        async def ainvoke(self, messages):
                            return {"response": f"This is a mock response for: {messages.get('messages', '')}"}
                    
                    # Create the agent with tools from the server
                    tools = client.get_tools()
                    agent = create_react_agent(model=MockLLM(), tools=tools)
                    
                    # Get prompt from server
                    prompt_name = prompt_map[prompt_type]
                    prompt_from_server = await client.get_prompt(
                        server_name="DataFlyWheelServer",
                        prompt_name=prompt_name,
                        arguments={}
                    )
                    
                    # Format the prompt
                    if "{query}" in prompt_from_server[0].content:
                        formatted_prompt = prompt_from_server[0].content.format(query=query_text)
                    else:
                        formatted_prompt = prompt_from_server[0].content + query_text
                    
                    # Show testing result
                    result = f"""
                    === Server Connection Test ===
                    
                    ✅ Successfully connected to server
                    ✅ Retrieved prompt: "{prompt_name}"
                    ✅ Found {len(tools)} tools
                    
                    === Query Information ===
                    Your query: {query_text}
                    
                    === In Production ===
                    In a production environment with the real LLM, this query would be processed
                    using the {prompt_type} prompt and the available tools.
                    
                    To see a full list of available prompts, tools, and resources, check the tabs
                    in the sidebar.
                    """
                    
                    # Update placeholder with result
                    message_placeholder.text(result)
                    
                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    
            except Exception as e:
                error_message = f"Error processing query: {str(e)}"
                message_placeholder.text(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

    # Process query when submitted
    if query:
        # Check if connected to server
        if not st.session_state.server_connected:
            st.warning("Please connect to the server first using the button in the sidebar")
        else:
            # Use asyncio to run the async function
            asyncio.run(process_query(query))

with chat_col2:
    # Example queries based on prompt type
    st.subheader("Example Queries")
    examples = {
        "Calculator": ["(4+5)/2.0", "sqrt(16) + 7", "3^4 - 12"],
        "HEDIS Expert": [
            "What are the different race stratification for CBP HEDIS Reporting?",
            "What are the different HCPCS codes in the Colonoscopy Value set?",
            "Describe Care for Older Adults Measure"
        ],
        "Weather": [
            "What is the present weather in Richmond?",
            "What's the weather forecast for Atlanta?",
            "Is it raining in New York City today?"
        ]
    }
    
    # Show examples for the selected prompt type
    for example in examples[prompt_type]:
        if st.button(example, key=f"example_{example}"):
            # Set as if user had entered this query
            asyncio.run(process_query(example))
    
    # Clear chat button
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.experimental_rerun()

# Add a footer
st.markdown("---")
st.markdown("Healthcare AI Assistant powered by MCP and LangChain")
