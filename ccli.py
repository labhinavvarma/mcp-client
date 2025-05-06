import streamlit as st
import asyncio
import json
import yaml
from mcp import ClientSession
from mcp.client.sse import sse_client

# Page configuration
st.set_page_config(page_title="MCP Server Inspector", page_icon="🔌", layout="wide")

# App title
st.title("MCP Server Inspector")
st.markdown("Inspect your MCP server's resources, tools, and prompts")

# Initialize session state
if "connected" not in st.session_state:
    st.session_state.connected = False
if "connection_error" not in st.session_state:
    st.session_state.connection_error = None
if "server_tabs_index" not in st.session_state:
    st.session_state.server_tabs_index = 0

# Helper function to run async code
def async_fetch(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Server connection
st.sidebar.header("Server Connection")
server_url = st.sidebar.text_input("Server URL", value="http://10.126.192.183:8001/sse")

# Connection functions
async def connect_to_server(url):
    try:
        sse_connection = await sse_client(url=url)
        session = await ClientSession(*sse_connection).__aenter__()
        await session.initialize()
        return session, sse_connection
    except Exception as e:
        return None, None, str(e)

# Define async fetch functions
async def fetch_prompts(session):
    try:
        return await session.list_prompts()
    except Exception as e:
        return f"Error: {str(e)}"

async def fetch_tools(session):
    try:
        return await session.list_tools()
    except Exception as e:
        return f"Error: {str(e)}"

async def fetch_resources(session):
    try:
        return await session.list_resources()
    except Exception as e:
        return f"Error: {str(e)}"

async def fetch_yaml_content(session):
    try:
        return await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
    except Exception as e:
        return f"Error: {str(e)}"

async def fetch_search_objects(session):
    try:
        return await session.read_resource("search://cortex_search/search_obj/list")
    except Exception as e:
        return f"Error: {str(e)}"

# Connect button
if st.sidebar.button("Connect to Server"):
    with st.sidebar.spinner("Connecting..."):
        # Clear previous connection state
        if "session" in st.session_state:
            del st.session_state.session
        if "sse_connection" in st.session_state:
            del st.session_state.sse_connection
        
        # Try to connect
        try:
            session, sse_connection = async_fetch(connect_to_server(server_url))
            if session and sse_connection:
                st.session_state.session = session
                st.session_state.sse_connection = sse_connection
                st.session_state.connected = True
                st.session_state.connection_error = None
                st.sidebar.success("✅ Connected to server!")
            else:
                st.session_state.connected = False
                st.session_state.connection_error = "Failed to connect to server"
                st.sidebar.error("❌ Connection failed!")
        except Exception as e:
            st.session_state.connected = False
            st.session_state.connection_error = str(e)
            st.sidebar.error(f"❌ Connection error: {str(e)}")

# Main content
if st.session_state.connected and "session" in st.session_state:
    # Server information tabs
    tabs = st.tabs(["Prompts", "Tools", "Resources", "YAML Content", "Search Objects"])
    
    # Prompts tab
    with tabs[0]:
        st.header("Available Prompts")
        if st.button("Refresh Prompts"):
            with st.spinner("Fetching prompts..."):
                prompts_result = async_fetch(fetch_prompts(st.session_state.session))
                st.session_state.prompts_result = prompts_result
        
        if "prompts_result" not in st.session_state:
            with st.spinner("Fetching prompts..."):
                prompts_result = async_fetch(fetch_prompts(st.session_state.session))
                st.session_state.prompts_result = prompts_result
        
        # Display prompts
        if isinstance(st.session_state.prompts_result, str) and st.session_state.prompts_result.startswith("Error"):
            st.error(st.session_state.prompts_result)
        elif hasattr(st.session_state.prompts_result, 'prompts') and st.session_state.prompts_result.prompts:
            # Use a set to track prompt names to avoid duplicates
            seen_prompts = set()
            for prompt in st.session_state.prompts_result.prompts:
                if prompt.name not in seen_prompts:
                    seen_prompts.add(prompt.name)
                    with st.expander(f"📝 {prompt.name}"):
                        st.write(f"**Description:** {prompt.description if hasattr(prompt, 'description') and prompt.description else 'No description'}")
                        
                        # Display arguments if available
                        if hasattr(prompt, 'arguments') and prompt.arguments:
                            st.write("**Arguments:**")
                            for arg in prompt.arguments:
                                required_str = "[Required]" if arg.required else "[Optional]"
                                st.write(f"- {arg.name} {required_str}: {arg.description if hasattr(arg, 'description') else ''}")
        else:
            st.info("No prompts found or prompts information unavailable")
    
    # Tools tab
    with tabs[1]:
        st.header("Available Tools")
        if st.button("Refresh Tools"):
            with st.spinner("Fetching tools..."):
                tools_result = async_fetch(fetch_tools(st.session_state.session))
                st.session_state.tools_result = tools_result
        
        if "tools_result" not in st.session_state:
            with st.spinner("Fetching tools..."):
                tools_result = async_fetch(fetch_tools(st.session_state.session))
                st.session_state.tools_result = tools_result
        
        # Display tools
        if isinstance(st.session_state.tools_result, str) and st.session_state.tools_result.startswith("Error"):
            st.error(st.session_state.tools_result)
        elif hasattr(st.session_state.tools_result, 'tools') and st.session_state.tools_result.tools:
            # Use a set to track tool names to avoid duplicates
            seen_tools = set()
            for tool in st.session_state.tools_result.tools:
                if tool.name not in seen_tools:
                    seen_tools.add(tool.name)
                    with st.expander(f"🔧 {tool.name}"):
                        st.write(f"**Description:** {tool.description if hasattr(tool, 'description') and tool.description else 'No description'}")
        else:
            st.info("No tools found or tools information unavailable")
    
    # Resources tab
    with tabs[2]:
        st.header("Available Resources")
        if st.button("Refresh Resources"):
            with st.spinner("Fetching resources..."):
                resources_result = async_fetch(fetch_resources(st.session_state.session))
                st.session_state.resources_result = resources_result
        
        if "resources_result" not in st.session_state:
            with st.spinner("Fetching resources..."):
                resources_result = async_fetch(fetch_resources(st.session_state.session))
                st.session_state.resources_result = resources_result
        
        # Display resources
        if isinstance(st.session_state.resources_result, str) and st.session_state.resources_result.startswith("Error"):
            st.error(st.session_state.resources_result)
        elif hasattr(st.session_state.resources_result, 'resources') and st.session_state.resources_result.resources:
            for resource in st.session_state.resources_result.resources:
                with st.expander(f"📚 {resource.name}"):
                    st.write(f"**Description:** {resource.description if hasattr(resource, 'description') and resource.description else 'No description'}")
                    
                    # Check if the resource is parametric
                    if '{' in resource.name:
                        st.write(f"**[PARAMETRIC] Parameters:**")
                        
                        # Extract all parameters
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
            st.info("No resources found or resources information unavailable")
    
    # YAML Content tab
    with tabs[3]:
        st.header("YAML Content")
        if st.button("Refresh YAML Content"):
            with st.spinner("Fetching YAML content..."):
                yaml_result = async_fetch(fetch_yaml_content(st.session_state.session))
                st.session_state.yaml_result = yaml_result
        
        if "yaml_result" not in st.session_state:
            with st.spinner("Fetching YAML content..."):
                yaml_result = async_fetch(fetch_yaml_content(st.session_state.session))
                st.session_state.yaml_result = yaml_result
        
        # Display YAML content
        if isinstance(st.session_state.yaml_result, str) and st.session_state.yaml_result.startswith("Error"):
            st.error(st.session_state.yaml_result)
        elif hasattr(st.session_state.yaml_result, 'contents') and st.session_state.yaml_result.contents:
            for item in st.session_state.yaml_result.contents:
                if hasattr(item, 'text'):
                    try:
                        # Parse YAML content
                        parsed_yaml = yaml.safe_load(item.text)
                        
                        # Convert back to YAML with nice formatting
                        formatted_yaml = yaml.dump(parsed_yaml, default_flow_style=False, sort_keys=False)
                        
                        st.code(formatted_yaml, language="yaml")
                    except yaml.YAMLError as e:
                        st.error(f"Failed to parse YAML: {e}")
                        st.code(item.text)
        else:
            st.info("No YAML content found or YAML information unavailable")
    
    # Search Objects tab
    with tabs[4]:
        st.header("Search Objects")
        if st.button("Refresh Search Objects"):
            with st.spinner("Fetching search objects..."):
                search_result = async_fetch(fetch_search_objects(st.session_state.session))
                st.session_state.search_result = search_result
        
        if "search_result" not in st.session_state:
            with st.spinner("Fetching search objects..."):
                search_result = async_fetch(fetch_search_objects(st.session_state.session))
                st.session_state.search_result = search_result
        
        # Display search objects
        if isinstance(st.session_state.search_result, str) and st.session_state.search_result.startswith("Error"):
            st.error(st.session_state.search_result)
        elif hasattr(st.session_state.search_result, 'contents') and st.session_state.search_result.contents:
            for item in st.session_state.search_result.contents:
                if hasattr(item, 'text'):
                    try:
                        objects = json.loads(item.text)
                        st.json(objects)
                    except json.JSONDecodeError as e:
                        st.error(f"Failed to parse JSON: {e}")
                        st.code(item.text)
        else:
            st.info("No search objects found or search information unavailable")

    # Disconnect button
    if st.sidebar.button("Disconnect"):
        if "session" in st.session_state:
            try:
                # Properly close session
                async_fetch(st.session_state.session.__aexit__(None, None, None))
            except:
                pass
            del st.session_state.session
        
        if "sse_connection" in st.session_state:
            try:
                # Properly close connection
                async_fetch(st.session_state.sse_connection.__aexit__(None, None, None))
            except:
                pass
            del st.session_state.sse_connection
        
        st.session_state.connected = False
        st.experimental_rerun()

else:
    if st.session_state.connection_error:
        st.error(f"Connection error: {st.session_state.connection_error}")
    
    st.info("Please connect to an MCP server using the sidebar controls.")
    
    # Example of server URL explanation
    st.markdown("""
    ### How to Connect
    1. Enter your MCP server URL in the sidebar
    2. Click "Connect to Server"
    3. Explore the tabs to view server information
    
    ### Server URL format
    The typical format is: `http://hostname:port/sse`
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("MCP Server Inspector v1.0")
