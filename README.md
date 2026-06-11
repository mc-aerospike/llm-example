# Local LLM Thread Manager

A Python application for managing chat conversations with a local LLM using Ollama and Aerospike for persistent storage.

## Features

- **Thread Management**: Create and manage multiple independent chat threads
- **Local LLM Support**: Uses Ollama to run LLMs locally
- **Persistent Storage**: Chat history stored in Aerospike database
- **Interactive CLI**: Menu-driven interface for thread selection and conversation management

## Requirements

- Python 3.x
- Ollama running locally
- Aerospike database (local or remote)
- Dependencies listed in `requirements.txt`

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   Create a `.env` file in the project root with:
   ```
   AEROSPIKE_HOST=127.0.0.1
   AEROSPIKE_PORT=3100
   AEROSPIKE_NAMESPACE=test
   AEROSPIKE_SET=local_llm_history
   AEROSPIKE_SET_SEEDS=True
   ```

3. **Start Ollama** (if not already running):
   ```bash
   ollama serve
   ```

4. **Run the application**:
   ```bash
   python app_llm.py
   ```

## Usage

- Launch the app to see a menu of existing threads
- Select a thread number to continue a conversation
- Select `[N]` to create a new thread
- Select `[M]` to manage threads (rename or delete)
- Enter your messages and interact with the local LLM
- Type `exit` or `quit` to return to the main menu

### Thread Management

**Renaming a thread:**
1. Select `[M]` from the main menu
2. Choose the thread to rename
3. Enter the new name

**Deleting a thread:**
1. Select `[M]` from the main menu
2. Choose the thread to delete
3. Confirm deletion with `yes`
4. The thread and all its chat history will be permanently removed


## Project Structure

- `app_llm.py` - Main application with thread management and chat logic
- `requirements.txt` - Python package dependencies
- `.env` - Environment configuration (create this file)
