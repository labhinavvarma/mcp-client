import streamlit as st
import asyncio
import nest_asyncio
import json
import yaml

from mcp.client.sse import sse_client
from mcp import ClientSession

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from dependencies import SnowFlakeConnector
from llmobject_wrapper import ChatSnowflakeCortex
from snowflake.snowpark import Session

# Page config
st.set_page_config(page_title="Healthcare AI Chat", page_icon="🏥")
st.title("Healthcare AI Chat")

nest_asyncio.apply()

# --- Sidebar Configuration ---
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
show_server_info = st.sidebar.checkbox("🛡 Show MCP Server Info", value=False)

# --- Show Server Information ---
if show_server_info:
    async def fetch_mcp_info():
        result = {"resources": [], "tools": [], "prompts": [], "yaml": []}
        try:
            async with sse_client(url=server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()
                    resources = await session.list_resources()
                    if hasattr(resources, 'resources'):
                        for r in resources.resources:
                            result["resources"].append({"name": r.name, "description": r.description})

                    tools = await session.list_tools()
                    if hasattr(tools, 'tools'):
                        for t in tools.tools:
                            result["tools"].append({"name": t.name, "description": getattr(t, 'description', 'No description')})

                    prompts = await session.list_prompts()
                    if hasattr(prompts, 'prompts'):
                        for p in prompts.prompts:
                            args = []
                            if hasattr(p, 'arguments'):
                                for arg in p.arguments:
                                    args.append(f"{arg.name} ({'Required' if arg.required else 'Optional'}): {arg.description}")
                            result["prompts"].append({
                                "name": p.name,
                                "description": getattr(p, 'description', ''),
                                "args": args
                            })

                    try:
                        yaml_content = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                        if hasattr(yaml_content, 'contents'):
                            for item in yaml_content.contents:
                                if hasattr(item, 'text'):
                                    parsed = yaml.safe_load(item.text)
                                    result["yaml"].append(yaml.dump(parsed, sort_keys=False))
                    except Exception as e:
                        result["yaml"].append(f"YAML error: {e}")

        except Exception as e:
            st.sidebar.error(f"❌ MCP Connection Error: {e}")
        return result

    mcp_data = asyncio.run(fetch_mcp_info())

    with st.sidebar.expander("📦 Resources", expanded=False):
        for r in mcp_data["resources"]:
            st.markdown(f"**{r['name']}**\n\n{r['description']}")

    with st.sidebar.expander("🛠 Tools", expanded=False):
        for t in mcp_data["tools"]:
            st.markdown(f"**{t['name']}**\n\n{t['description']}")

    with st.sidebar.expander("🧐 Prompts", expanded=False):
        for p in mcp_data["prompts"]:
            st.markdown(f"**{p['name']}**\n\n{p['description']}")
            if p["args"]:
                st.markdown("Arguments:")
                for a in p["args"]:
                    st.markdown(f"- {a}")

    with st.sidebar.expander("📄 YAML", expanded=False):
        for y in mcp_data["yaml"]:
            st.code(y, language="yaml")

else:
    # Re-enable Snowflake and LLM chatbot features
    @st.cache_resource
    def get_snowflake_connection():
        return SnowFlakeConnector.get_conn('aedl', '')

    @st.cache_resource
    def get_model():
        sf_conn = get_snowflake_connection()
        return ChatSnowflakeCortex(
            model="llama3.1-70b-elevance",
            cortex_function="complete",
            session=Session.builder.configs({"connection": sf_conn}).getOrCreate()
        )

    prompt_type = st.sidebar.radio("Select Prompt Type", ["Calculator", "HEDIS Expert", "Weather"])
    prompt_map = {
        "Calculator": "calculator-prompt",
        "HEDIS Expert": "hedis-prompt",
        "Weather": "weather-prompt"
    }
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
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    with st.sidebar.expander("Example Queries", expanded=True):
        for example in examples[prompt_type]:
            if st.button(example, key=example):
                st.session_state.query_input = example

    query = st.chat_input("Type your query here...")
    if "query_input" in st.session_state:
        query = st.session_state.query_input
        del st.session_state.query_input

    async def process_query(query_text):
        st.session_state.messages.append({"role": "user", "content": query_text})
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.text("Processing...")
            try:
                async with MultiServerMCPClient(
                    {"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}
                ) as client:
                    model = get_model()
                    agent = create_react_agent(model=model, tools=client.get_tools())
                    prompt_name = prompt_map[prompt_type]
                    prompt_from_server = await client.get_prompt(
                        server_name="DataFlyWheelServer",
                        prompt_name=prompt_name,
                        arguments={}
                    )
                    if "{query}" in prompt_from_server[0].content:
                        formatted_prompt = prompt_from_server[0].content.format(query=query_text)
                    else:
                        formatted_prompt = prompt_from_server[0].content + query_text
                    response = await agent.ainvoke({"messages": formatted_prompt})
                    result = list(response.values())[0][1].content
                    message_placeholder.text(result)
                    st.session_state.messages.append({"role": "assistant", "content": result})
            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.text(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

    if query:
        asyncio.run(process_query(query))

    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.experimental_rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("Healthcare AI Chat v1.0")
