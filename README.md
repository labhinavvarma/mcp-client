# 🚀 MCP Client with Gemini AI

[📢 Subscribe to The AI Language on YouTube!](https://youtube.com/@theailanguage?sub_confirmation=1)

Happy building, and don’t forget to subscribe!  

---

**Table of Contents**
- [✪ Features](#-features)
- [὎6 Installation](#-installation)
- [🔑 Setting Up the API Key](#-setting-up-the-api-key)
- [🚀 Running the MCP Client](#-running-the-mcp-client)
- [🔧 How It Works](#-how-it-works)
- [📁 Project Structure](#-project-structure)
- [🎯 Example](#-example)
- [🌟 Contributing](#-contributing)
- [🎮 Tutorial Videos](#-tutorial-videos)

You now have **three different MCP client implementations** in this repo:

### ➔ Option 1: Legacy Client (with Gemini but without LangChain)
```bash
uv run client.py path/to/server.py
```

### ➔ Option 2: New LangChain Client (with Gemini + React Agent)
```bash
uv run langchain_mcp_client.py path/to/server.py
```

### ➔ Option 3: New LangChain Client (with Gemini + React Agent, Multi-Server Config)
```bash
uv run langchain_mcp_client_wconfig.py path/to/config.json
```

If you want to add preexisting MCP Servers, please refer to [this repository](https://github.com/modelcontextprotocol/servers).

Watch the multi-server tutorial video 👉 [https://youtu.be/nCnBWVv2uTA](https://youtu.be/nCnBWVv2uTA)

[![Multi-Server Tutorial Video](https://img.youtube.com/vi/nCnBWVv2uTA/maxresdefault.jpg)](https://youtu.be/nCnBWVv2uTA)

---

## ✪ **Features**
✅ Connects to an MCP server (Python or Node.js)  
✅ Sends queries to **Google Gemini AI**  
✅ Lets **Gemini call external tools** from the MCP server  
✅ Executes MCP tool commands and **returns the results**  
✅ (in progress) **Maintains conversation history**, so Gemini **remembers past queries**       

---

## 📦 **Installation**

**1⃣ Install the required dependencies using `uv` (Universal Virtualenv):**
```bash
uv add mcp python-dotenv google-genai
```

**2⃣ Clone this repository:**
```bash
cd mcp-client-gemini
```

**3⃣ Set up the project and virtual environment:**
```bash
uv init mcp-client
cd mcp-client
uv venv
```

**4⃣ Activate the virtual environment:**
```bash
# On Windows:
.venv\Scripts\activate

# On MacOS/Linux:
source .venv/bin/activate
```

---

## 🔑 **Setting Up the API Key**

To use **Google Gemini AI**, you need an **API key**. Please go to [Google AI Studio](https://aistudio.google.com/prompts/new_chat). Please read their terms and conditions and other policies before obtaining and using the key.

**1⃣ Create a `.env` file:**
```bash
touch .env
```

**2⃣ Add your API key inside `.env`:**
```
GEMINI_API_KEY=your_api_key_here
GOOGLE_API_KEY=your_api_key_here
```

**3⃣ Make sure `.env` is ignored in Git:**
```bash
echo ".env" >> .gitignore
```

*Note:* If you're using the new LangChain client, you can also name the key `GOOGLE_API_KEY`. The client will automatically load it using `dotenv`.

---

## 🚀 **Running the MCP Client**

You now have **three different MCP client implementations** in this repo:

### ➔ Option 1: Legacy Client (Without LangChain)
```bash
uv run client.py path/to/server.py
```

### ➔ Option 2: New LangChain Client (with Gemini + React Agent)
```bash
uv run langchain_mcp_client.py path/to/server.py
```

### ➔ Option 3: New LangChain Client (with Gemini + React Agent, Multi-Server Config)
```bash
uv run langchain_mcp_client_wconfig.py
```

Watch the respective tutorial videos:  
Legacy Client Tutorial 👉 [https://youtu.be/GAPncIfnDwg](https://youtu.be/GAPncIfnDwg)  
LangChain Client Tutorial 👉 [https://youtu.be/hccNm88bk6w](https://youtu.be/hccNm88bk6w)  
Multi-Server LangChain Client Tutorial 👉 [https://youtu.be/nCnBWVv2uTA](https://youtu.be/nCnBWVv2uTA)

---

## 🔧 **How It Works**

1⃣ You enter a query like:  
`Create a file named test.txt`

2⃣ The MCP client sends this to **Google Gemini AI**

3⃣ Gemini sees available MCP tools and calls the correct one (e.g. `run_command`)

4⃣ The MCP client executes the command via the server and returns the result

5⃣ Gemini responds with context-aware output and remembers previous interactions

---

## 📁 **Project Structure**
```
mcp-client-gemini/
│— client.py                        # Legacy MCP Client (without LangChain)
│— langchain_mcp_client.py          # New MCP Client using LangChain & Gemini
│— langchain_mcp_client_wconfig.py  # New LangChain Client with multi-server configuration support
│— .env                             # Stores your Google Gemini API key
│— README.md                        # This documentation
│— requirements.txt                 # Optional dependency list
│— .gitignore                       # To ignore .env and other files
│— LICENSE                          # License file
```

---

## 🎯 **Example**

Run with a terminal server:
```bash
uv run langchain_mcp_client.py ../../servers/terminal_server/terminal_server.py
```

Query:
```
create file notes.txt and write hello inside
```

Output:
```json
{
  "messages": [
    {
      "type": "HumanMessage",
      "content": "create file notes.txt and write hello inside"
    },
    {
      "type": "AIMessage",
      "content": "Sure! I will create notes.txt and add 'hello' inside it."
    }
  ]
}
```

---

## 🌟 **Contributing**

If you'd like to add more client versions to help people learn the same concepts, please consider contributing!  
✅ Submit bug fixes or ideas  
✅ Help improve documentation

Just fork this repo and submit a pull request.

---

## 🎮 **Tutorial Videos**

🎥 Legacy MCP Client Tutorial  
👉 [https://youtu.be/GAPncIfnDwg](https://youtu.be/GAPncIfnDwg)

🎥 LangChain + Gemini MCP Client Tutorial  
👉 [https://youtu.be/hccNm88bk6w](https://youtu.be/hccNm88bk6w)

🎥 Multi-Server LangChain Client Tutorial  
👉 [https://youtu.be/nCnBWVv2uTA](https://youtu.be/nCnBWVv2uTA)