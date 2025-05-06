import streamlit as st
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Page configuration
st.set_page_config(page_title="MCP Testing Interface", page_icon="🔌")

# App title
st.title("MCP Testing Interface")
st.markdown("This interface tests only the MCP connection without LLM or Snowflake.")

# Server configuration
with st.sidebar.expander("Server Configuration", expanded=True):
    server_url = st.text_input("Server URL", value="http://10.126.192.183:8000/sse")
    server_transport = st.selectbox("Transport", ["sse"], index=0)

# Prompt selection
prompt_type = st.sidebar.radio(
    "Select Prompt Type",
    ["Calculator", "HEDIS Expert", "Weather"]
)

prompt_map = {
    "Calculator": "calculator-prompt",
    "HEDIS Expert": "hedis-prompt",
    "Weather": "weather-prompt"
}

# Chat history container
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Example queries based on prompt type
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

# Show example queries
with st.sidebar.expander("Example Queries", expanded=True):
    st.write("Click an example to use it:")
    for example in examples[prompt_type]:
        if st.button(example, key=example):
            # Set the query input to this example
            st.session_state.query_input = example

# Input for the query
query = st.chat_input("Type your query here...")
if "query_input" in st.session_state:
    query = st.session_state.query_input
    del st.session_state.query_input

# Mock response function (since we don't have the real LLM)
def get_mock_response(prompt_type, query):
    """Generate a mock response for testing without the LLM"""
    if prompt_type == "Calculator":
        return f"[MOCK] Calculator result for: {query}\nThis would normally calculate the result using the MCP server."
    elif prompt_type == "HEDIS Expert":
        return f"[MOCK] HEDIS information for: {query}\nThis would normally return healthcare standards information."
    else:  # Weather
        return f"[MOCK] Weather information for: {query}\nThis would normally return weather data."

# Function to process query
async def process_query(query_text):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query_text})
    
    # Create a placeholder for the response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.text("Connecting to MCP server...")
        
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
                # Get prompt from server based on selection
                prompt_name = prompt_map[prompt_type]
                
                # Log the connection status
                message_placeholder.text(f"Connected to server. Retrieving prompt: {prompt_name}...")
                
                try:
                    # Attempt to get the prompt from the server
                    prompt_from_server = await client.get_prompt(
                        server_name="DataFlyWheelServer",
                        prompt_name=prompt_name,
                        arguments={}
                    )
                    
                    # Format the prompt (for display purposes only)
                    if prompt_from_server and len(prompt_from_server) > 0:
                        if "{query}" in prompt_from_server[0].content:
                            formatted_prompt = prompt_from_server[0].content.format(query=query_text)
                        else:
                            formatted_prompt = prompt_from_server[0].content + query_text
                        
                        prompt_info = f"Successfully retrieved prompt: {prompt_name}\n\n"
                        prompt_preview = f"Prompt preview (first 100 chars):\n{formatted_prompt[:100]}...\n\n"
                    else:
                        prompt_info = f"Retrieved empty prompt from server.\n\n"
                        prompt_preview = ""
                    
                    # Display the tools available
                    tools = client.get_tools()
                    tools_info = f"Available tools: {', '.join([tool.name for tool in tools]) if tools else 'None'}\n\n"
                    
                    # Generate a mock response since we don't have the LLM
                    mock_response = get_mock_response(prompt_type, query_text)
                    
                    # Compile the complete response
                    result = f"{prompt_info}{prompt_preview}{tools_info}Mock response:\n{mock_response}"
                    
                except Exception as e:
                    result = f"Error retrieving prompt: {str(e)}\nServer connected, but prompt retrieval failed."
                
                # Update the placeholder with the result
                message_placeholder.text(result)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": result})
                
        except Exception as e:
            error_message = f"MCP Connection Error: {str(e)}\nFailed to connect to the MCP server."
            message_placeholder.text(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Process query when submitted
if query:
    # Use asyncio to run the async function
    asyncio.run(process_query(query))

# Debug section
with st.sidebar.expander("Debug Options", expanded=False):
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.experimental_rerun()
    
    if st.button("Show Session State"):
        st.write(st.session_state)

# Add a small footer
st.sidebar.markdown("---")
st.sidebar.markdown("MCP Testing Interface v1.0")

# Additional information display
st.sidebar.markdown("---")
st.sidebar.markdown("""
### About This Interface
This is a simplified testing interface that only connects to the MCP server without using 
the LLM or Snowflake connections. It retrieves prompts from the server and displays information
about the connection, available tools, and prompt content.

The responses are mocked since we don't have the actual LLM integration.
""")
