# chatbot_app.py
# All-in-one FastAPI chatbot that routes to the appropriate tool based on the query

import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional, Any, Union

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# LangChain imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Snowflake imports
from snowflake.snowpark import Sessionxss

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chatbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

#################################################
# Snowflake Connector
#################################################

class SnowFlakeConnector:
    @staticmethod
    def get_conn(environment, additional_config=None):
        """
        Get Snowflake connection parameters based on environment
        
        Args:
            environment (str): Environment name (e.g., 'aedl')
            additional_config (dict, optional): Additional configuration parameters
            
        Returns:
            dict: Snowflake connection parameters
        """
        # This is a placeholder - replace with actual connection logic
        if environment == 'aedl':
            conn_params = {
                'account': 'your_snowflake_account',
                'user': 'your_username',
                'password': 'your_password',
                'warehouse': 'your_warehouse',
                'database': 'your_database',
                'schema': 'your_schema',
                'role': 'your_role',
            }
        else:
            conn_params = {
                'account': 'default_account',
                'user': 'default_user',
                'password': 'default_password',
                'warehouse': 'default_warehouse',
                'database': 'default_database',
                'schema': 'default_schema',
                'role': 'default_role',
            }
            
        # Add any additional config parameters
        if additional_config:
            conn_params.update(additional_config)
            
        return conn_params

#################################################
# LLM Wrapper
#################################################

class ChatSnowflakeCortex(ChatOpenAI):
    """
    Wrapper class for Snowflake Cortex integration with LangChain
    
    This class extends ChatOpenAI to integrate with Snowflake Cortex for
    language model inference. It handles communication with Snowflake,
    leveraging Cortex functions for inference.
    """
    
    def __init__(
        self,
        model: str,
        cortex_function: str,
        session: Session,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ):
        """
        Initialize the ChatSnowflakeCortex wrapper
        
        Args:
            model (str): Model name to use with Cortex
            cortex_function (str): Cortex function name to call
            session (Session): Snowflake Snowpark session
            temperature (float, optional): Sampling temperature. Defaults to 0.7.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 1024.
            **kwargs: Additional arguments to pass to the parent class
        """
        # Initialize parent class
        super().__init__(
            model_name=model, 
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Store Cortex-specific parameters
        self.cortex_function = cortex_function
        self.session = session
        logger.info(f"Initialized ChatSnowflakeCortex with model: {model}")
        
    def _generate_cortex_parameters(self, prompt: str) -> Dict[str, Any]:
        """
        Generate parameters for Cortex function call
        
        Args:
            prompt (str): Input prompt text
            
        Returns:
            Dict[str, Any]: Parameters for Cortex function
        """
        return {
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
    def _call(self, prompt: str, **kwargs) -> str:
        """
        Override _call to use Snowflake Cortex
        
        Args:
            prompt (str): Input prompt
            **kwargs: Additional arguments
            
        Returns:
            str: Model response
        """
        try:
            logger.info("Calling Snowflake Cortex for inference")
            
            # Generate parameters for Cortex
            params = self._generate_cortex_parameters(prompt)
            
            # In a real implementation, you would call Cortex like this:
            # result = self.session.sql(
            #     f"SELECT {self.cortex_function}(
            #         :prompt, 
            #         :temperature, 
            #         :max_tokens
            #     ) AS response", 
            #     params=params
            # ).collect()[0]['RESPONSE']
            
            # For now, we're just passing through to the parent class
            result = super()._call(prompt, **kwargs)
            
            logger.info("Successfully received response from Cortex")
            return result
            
        except Exception as e:
            logger.error(f"Error calling Cortex: {str(e)}")
            # Return error message or fallback to parent class
            return f"Error: {str(e)}"

#################################################
# Chatbot Client
#################################################

class ChatbotConfig:
    """Configuration class for Chatbot settings"""
    
    def __init__(
        self,
        environment: str = 'aedl',
        model_name: str = "llama3.1-70b-elevance",
        cortex_function: str = "complete",
        server_url: str = "http://10.126.192.183:8000/sse",
        server_name: str = "DataFlyWheelServer",
        transport: str = "sse",
        default_system_prompt: Optional[str] = None
    ):
        self.environment = environment
        self.model_name = model_name
        self.cortex_function = cortex_function
        self.server_url = server_url
        self.server_name = server_name
        self.transport = transport
        
        # Default system prompt if none provided
        if default_system_prompt is None:
            self.default_system_prompt = """
            You are a helpful assistant with access to multiple tools. Based on the user's question,
            you will automatically determine which tool is most appropriate and use it to provide
            an answer. Your available tools include:
            1) DFWAnalyst - Generates SQL to retrieve information for HEDIS codes and value sets.
            2) DFWSearch - Provides HEDIS measures, standards, and criteria from specification documents.
            3) Calculator - Performs mathematical calculations and verifies results.
            4) Weather - Provides current weather information for locations.
            """
        else:
            self.default_system_prompt = default_system_prompt


class ChatbotClient:
    """Client for interacting with LLM and tools"""
    
    def __init__(self, config: ChatbotConfig):
        """Initialize the chatbot client with configuration"""
        self.config = config
        self.agent = None
        self.mcp_client = None
        self.system_prompt = config.default_system_prompt
        self.sf_session = None
        self.model = None
        self.chat_history = []
        self._initialize_snowflake()
        self._initialize_model()
        
    def _initialize_snowflake(self):
        """Initialize Snowflake connection"""
        try:
            logger.info("Initializing Snowflake connection")
            sf_conn = SnowFlakeConnector.get_conn(self.config.environment)
            self.sf_session = Session.builder.configs({"connection": sf_conn}).getOrCreate()
            logger.info("Snowflake connection established")
        except Exception as e:
            logger.error(f"Failed to initialize Snowflake connection: {str(e)}")
            raise
            
    def _initialize_model(self):
        """Initialize LLM model"""
        try:
            logger.info(f"Initializing model: {self.config.model_name}")
            self.model = ChatSnowflakeCortex(
                model=self.config.model_name,
                cortex_function=self.config.cortex_function,
                session=self.sf_session
            )
            logger.info("Model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise
            
    async def initialize(self):
        """Initialize MCP client and agent"""
        try:
            logger.info("Initializing MCP client")
            self.mcp_client = MultiServerMCPClient(
                {
                    self.config.server_name: {
                        "url": self.config.server_url,
                        "transport": self.config.transport,
                    }
                }
            )
            await self.mcp_client.__aenter__()
            
            # Create agent with tools
            logger.info("Creating agent with tools")
            self.agent = create_react_agent(
                model=self.model, 
                tools=self.mcp_client.get_tools()
            )
            
            # Try to get system prompt from server
            try:
                logger.info("Retrieving system prompt from server")
                base_prompt = await self.mcp_client.get_prompt(
                    server_name=self.config.server_name,
                    prompt_name="base-system-prompt",
                    arguments={}
                )
                if base_prompt and len(base_prompt) > 0:
                    self.system_prompt = base_prompt[0].content
                    logger.info("Retrieved system prompt from server")
            except Exception as e:
                logger.warning(f"Failed to retrieve system prompt, using default: {str(e)}")
            
            logger.info("Chatbot client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize client: {str(e)}")
            return False
            
    async def get_response(self, user_input: str) -> str:
        """
        Process user input and get response from agent
        
        Args:
            user_input (str): User's message
            
        Returns:
            str: Agent's response
        """
        if not self.agent:
            logger.error("Agent not initialized")
            return "Error: Agent not initialized. Please try again."
            
        try:
            logger.info(f"Processing user input: {user_input}")
            
            # Add user message to history
            self.chat_history.append({"role": "user", "content": user_input})
            
            # Format the full prompt with user input
            full_prompt = self.system_prompt + "\n\nUser Query: " + user_input
            
            # Get response from agent
            response = await self.agent.ainvoke({"messages": full_prompt})
            
            # Extract response
            bot_response = list(response.values())[0][1].content
            
            # Add bot response to history
            self.chat_history.append({"role": "assistant", "content": bot_response})
            
            logger.info(f"Generated response: {bot_response[:100]}...")
            return bot_response
        except Exception as e:
            error_message = f"Error processing your request: {str(e)}"
            logger.error(error_message)
            
            # Add error message to history
            self.chat_history.append({"role": "assistant", "content": error_message})
            return error_message
            
    async def close(self):
        """Close connections and clean up resources"""
        try:
            if self.mcp_client:
                await self.mcp_client.__aexit__(None, None, None)
            logger.info("Chatbot client closed")
        except Exception as e:
            logger.error(f"Error closing client: {str(e)}")

#################################################
# FastAPI App
#################################################

# Request models
class MessageRequest(BaseModel):
    message: str

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, str]]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "message": message,
                "sender": "bot"
            })

# Create FastAPI app
app = FastAPI(title="LLM Chatbot with Tool Routing")

# Create directory for templates if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Set up templates directory for HTML files
templates = Jinja2Templates(directory="templates")

# Store chat clients for each connection
chat_clients = {}

# Create connection manager
manager = ConnectionManager()

# HTML template for the chat interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Chatbot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f5f5f5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .chat-container {
            max-width: 800px;
            margin: 50px auto;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
        }
        .chat-header {
            background-color: #4a6fa5;
            color: white;
            padding: 15px 20px;
            font-weight: bold;
            font-size: 1.2em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-messages {
            height: 500px;
            overflow-y: auto;
            padding: 20px;
            background-color: white;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 80%;
            position: relative;
        }
        .user-message {
            background-color: #e3f2fd;
            margin-left: auto;
            border-bottom-right-radius: 0;
            text-align: right;
        }
        .bot-message {
            background-color: #f1f1f1;
            margin-right: auto;
            border-bottom-left-radius: 0;
        }
        .message-time {
            font-size: 0.7em;
            color: #888;
            margin-top: 5px;
        }
        .message-input {
            border-top: 1px solid #ddd;
            padding: 15px;
            background-color: white;
        }
        .spinner-border {
            width: 1rem;
            height: 1rem;
            margin-left: 10px;
            display: none;
        }
        .chat-tools {
            background-color: #eef5ff;
            padding: 10px 15px;
            font-size: 0.85em;
            color: #666;
        }
        .tool-badge {
            font-size: 0.8em;
            padding: 3px 8px;
            margin-right: 5px;
            background-color: #4a6fa5;
            color: white;
            border-radius: 10px;
        }
        .connection-status {
            font-size: 0.8em;
            display: flex;
            align-items: center;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        .connected {
            background-color: #28a745;
        }
        .disconnected {
            background-color: #dc3545;
        }
        .connecting {
            background-color: #ffc107;
        }
        #reset-chat {
            background: none;
            border: none;
            color: white;
            font-size: 0.9em;
            cursor: pointer;
            margin-left: 10px;
        }
        #reset-chat:hover {
            text-decoration: underline;
        }
        .chat-interface {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-container">
            <div class="chat-header">
                <div>LLM Chatbot with Tool Routing</div>
                <div class="d-flex align-items-center">
                    <div class="connection-status">
                        <span class="status-indicator disconnected" id="connection-indicator"></span>
                        <span id="connection-text">Disconnected</span>
                    </div>
                    <button id="reset-chat" title="Reset chat"><i class="bi bi-trash"></i> Reset</button>
                </div>
            </div>
            <div class="chat-tools">
                <span class="tool-badge">HEDIS</span>
                <span class="tool-badge">SQL</span>
                <span class="tool-badge">Calculator</span>
                <span class="tool-badge">Weather</span>
                Available tools - the assistant will automatically use the right one for your query
            </div>
            <div class="chat-interface">
                <div class="chat-messages" id="chat-messages">
                    <!-- Messages will be added here dynamically -->
                </div>
                <div class="message-input">
                    <form id="message-form" class="d-flex">
                        <input type="text" id="user-input" class="form-control me-2" placeholder="Type your message here..." autocomplete="off">
                        <button type="submit" class="btn btn-primary">
                            Send
                            <span class="spinner-border spinner-border-sm" id="loading-spinner" role="status" aria-hidden="true"></span>
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const messageForm = document.getElementById('message-form');
            const userInput = document.getElementById('user-input');
            const chatMessages = document.getElementById('chat-messages');
            const loadingSpinner = document.getElementById('loading-spinner');
            const resetButton = document.getElementById('reset-chat');
            const connectionIndicator = document.getElementById('connection-indicator');
            const connectionText = document.getElementById('connection-text');
            
            // Generate a unique client ID
            const clientId = Date.now().toString();
            
            // WebSocket connection
            let socket;
            let isWebSocketSupported = 'WebSocket' in window;
            
            // Connection status
            function updateConnectionStatus(status) {
                connectionIndicator.className = 'status-indicator ' + status;
                connectionText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            }
            
            // Initialize WebSocket if supported
            function initializeWebSocket() {
                if (isWebSocketSupported) {
                    updateConnectionStatus('connecting');
                    
                    // Create WebSocket connection
                    socket = new WebSocket(`ws://${window.location.host}/ws/${clientId}`);
                    
                    // Connection opened
                    socket.addEventListener('open', function(event) {
                        updateConnectionStatus('connected');
                    });
                    
                    // Listen for messages
                    socket.addEventListener('message', function(event) {
                        const data = JSON.parse(event.data);
                        
                        if (data.sender === 'bot') {
                            // Add bot message to chat
                            addMessage(data.message, 'bot');
                        }
                    });
                    
                    // Connection closed
                    socket.addEventListener('close', function(event) {
                        updateConnectionStatus('disconnected');
                        
                        // Try to reconnect after a delay
                        setTimeout(initializeWebSocket, 3000);
                    });
                    
                    // Connection error
                    socket.addEventListener('error', function(error) {
                        console.error('WebSocket error:', error);
                        updateConnectionStatus('disconnected');
                    });
                }
            }
            
            // Initialize WebSocket
            initializeWebSocket();
            
            // Add message to chat
            function addMessage(message, sender) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                
                // Message content
                messageDiv.textContent = message;
                
                // Timestamp
                const timeSpan = document.createElement('div');
                timeSpan.className = 'message-time';
                const now = new Date();
                timeSpan.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                messageDiv.appendChild(timeSpan);
                
                // Add to chat
                chatMessages.appendChild(messageDiv);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            // Handle form submission
            messageForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const message = userInput.value.trim();
                if (!message) return;
                
                // Add user message to chat
                addMessage(message, 'user');
                
                // Clear input
                userInput.value = '';
                
                // Show loading spinner
                loadingSpinner.style.display = 'inline-block';
                userInput.disabled = true;
                
                if (isWebSocketSupported && socket && socket.readyState === WebSocket.OPEN) {
                    // Send via WebSocket
                    socket.send(JSON.stringify({ message }));
                } else {
                    // Fallback to HTTP if WebSocket not available
                    try {
                        const response = await fetch('/api/send_message', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ message })
                        });
                        
                        const data = await response.json();
                        
                        if (data.error) {
                            // Show error message
                            addMessage(`Error: ${data.error}`, 'bot');
                        } else {
                            // Show response
                            addMessage(data.response, 'bot');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        addMessage('Sorry, there was an error processing your request.', 'bot');
                    }
                }
                
                // Hide loading spinner
                loadingSpinner.style.display = 'none';
                userInput.disabled = false;
                userInput.focus();
            });
            
            // Reset chat
            resetButton.addEventListener('click', async function() {
                if (confirm('Are you sure you want to reset the chat?')) {
                    try {
                        const response = await fetch('/api/reset', {
                            method: 'POST'
                        });
                        
                        const data = await response.json();
                        
                        if (data.status === 'success') {
                            // Clear chat
                            chatMessages.innerHTML = '';
                            
                            // Add welcome message
                            addMessage('Chat history has been reset. How can I help you today?', 'bot');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        addMessage('Sorry, there was an error resetting the chat.', 'bot');
                    }
                }
            });
            
            // Load chat history
            async function loadChatHistory() {
                try {
                    const response = await fetch('/api/history');
                    const data = await response.json();
                    
                    // Clear chat
                    chatMessages.innerHTML = '';
                    
                    // Add messages from history
                    if (data.history && data.history.length > 0) {
                        data.history.forEach(item => {
                            addMessage(item.content, item.role === 'user' ? 'user' : 'bot');
                        });
                    } else {
                        // Add welcome message if no history
                        addMessage('Hello! I\'m your assistant with access to HEDIS information, calculation tools, and more. How can I help you today?', 'bot');
                    }
                } catch (error) {
                    console.error('Error loading chat history:', error);
                    addMessage('Hello! I\'m your assistant with access to HEDIS information, calculation tools, and more. How can I help you today?', 'bot');
                }
            }
            
            // Load chat history on page load
            loadChatHistory();
        });
    </script>
</body>
</html>
"""

# Initialize chatbot client for a session
async def get_chat_client(client_id: str) -> ChatbotClient:
    """Get or create a chat client for the given client ID"""
    if client_id not in chat_clients:
        # Create configuration
        config = ChatbotConfig()
        
        # Create client
        client = ChatbotClient(config)
        
        # Initialize client
        initialized = await client.initialize()
        if not initialized:
            logger.error(f"Failed to initialize chatbot client for {client_id}")
            raise Exception("Failed to initialize chatbot client")
            
        # Store client
        chat_clients[client_id] = client
        
    return chat_clients[client_id]

# Cleanup chat client when connection closes
async def cleanup_chat_client(client_id: str):
    """Clean up resources for a chat client"""
    if client_id in chat_clients:
        client = chat_clients[client_id]
        await client.close()
        del chat_clients[client_id]
        logger.info(f"Cleaned up chat client for {client_id}")

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Serve the main page"""
    return HTMLResponse(content=HTML_TEMPLATE)

@app.post("/api/send_message")
async def send_message(message_request: MessageRequest, request: Request):
    """Handle message submission via HTTP POST"""
    # Generate a client ID from the request
    client_id = request.client.host
    
    try:
        # Get or create chat client
        client = await get_chat_client(client_id)
        
        # Get response
        response = await client.get_response(message_request.message)
        
        return JSONResponse({
            "response": response
        })
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@app.get("/api/history", response_model=ChatHistoryResponse)
async def get_history(request: Request):
    """Get chat history for the current session"""
    # Generate a client ID from the request
    client_id = request.client.host
    
    try:
        # Get chat client
        client = await get_chat_client(client_id)
        
        # Return history
        return ChatHistoryResponse(history=client.chat_history)
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return ChatHistoryResponse(history=[])

@app.post("/api/reset")
async def reset_chat(request: Request):
    """Reset chat history"""
    # Generate a client ID from the request
    client_id = request.client.host
    
    try:
        # Get chat client
        client = await get_chat_client(client_id)
        
        # Reset history
        client.chat_history = []
        
        return JSONResponse({
            "status": "success",
            "message": "Chat history reset"
        })
    except Exception as e:
        logger.error(f"Error resetting chat: {str(e)}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

# WebSocket endpoint for real-time chat
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Handle WebSocket connection for real-time chat"""
    try:
        # Accept connection
        await manager.connect(websocket, client_id)
        
        # Get or create chat client
        client = await get_chat_client(client_id)
        
        # Send welcome message
        await manager.send_message(
            "Hello! I'm your assistant with access to HEDIS information, calculation tools, and more. How can I help you today?",
            client_id
        )
        
        # Process messages
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                user_message = data.get("message", "")
                
                # Log message
                logger.info(f"Received message from {client_id}: {user_message}")
                
                # Process message
                response = await client.get_response(user_message)
                
                # Send response
                await manager.send_message(response, client_id)
                
        except WebSocketDisconnect:
            # Handle disconnect
            manager.disconnect(client_id)
            logger.info(f"Client {client_id} disconnected")
            
            # Clean up resources
            await cleanup_chat_client(client_id)
            
    except Exception as e:
        # Handle errors
        logger.error(f"WebSocket error for {client_id}: {str(e)}")
        manager.disconnect(client_id)
        await cleanup_chat_client(client_id)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("chatbot_app:app", host="0.0.0.0", port=8000, reload=True)
