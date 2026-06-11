import os
import sys
import uuid
from dotenv import load_dotenv
import ollama
import aerospike

# Load config from .env
load_dotenv()
NAMESPACE = os.getenv("AEROSPIKE_NAMESPACE", "test")
SET_NAME = os.getenv("AEROSPIKE_SET", "local_llm_history")
SET_SEEDS = os.getenv("AEROSPIKE_SET_SEEDS", "True")

# We will store the master list of all threads in a special single record
INDEX_RECORD_KEY = (NAMESPACE, SET_NAME, "master_thread_index")

def get_aerospike_client():
    if SET_SEEDS.lower() == "true":
        config = {
            'hosts': [
                ('127.0.0.1', 3100), ('127.0.0.1', 3101),
                ('127.0.0.1', 3102), ('127.0.0.1', 3103)
            ],
            'use_services_alternate': True 
        }
    else:
        config = {
            'hosts': [(os.getenv("AEROSPIKE_HOST", "127.0.0.1"), int(os.getenv("AEROSPIKE_PORT", 3100)))],
        }
    try:
        return aerospike.client(config)
    except Exception as e:
        print(f"Error connecting to your Aerolab cluster: {e}")
        sys.exit(1)

def get_thread_index(client):
    """Retrieves the directory of all threads {id: name}"""
    try:
        _, _, bins = client.get(INDEX_RECORD_KEY)
        return bins.get("threads", {})
    except aerospike.exception.RecordNotFound:
        return {}

def save_thread_index(client, thread_index):
    """Saves the updated directory back to Aerospike"""
    bins = {"threads": thread_index}
    client.put(INDEX_RECORD_KEY, bins)

def get_chat_history(client, thread_id):
    key = (NAMESPACE, SET_NAME, thread_id)
    try:
        _, _, bins = client.get(key)
        return bins.get("messages", [])
    except aerospike.exception.RecordNotFound:
        return []

def save_chat_history(client, thread_id, history):
    key = (NAMESPACE, SET_NAME, thread_id)
    bins = {"messages": history}
    client.put(key, bins)

def delete_thread(client, thread_id, thread_name):
    """Deletes a thread and its chat history from Aerospike"""
    try:
        # Remove from index
        threads = get_thread_index(client)
        if thread_id in threads:
            del threads[thread_id]
            save_thread_index(client, threads)
        
        # Delete chat history record
        key = (NAMESPACE, SET_NAME, thread_id)
        client.remove(key)
        print(f"✓ Thread '{thread_name}' has been deleted.")
        return True
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False

def rename_thread(client, thread_id, old_name):
    """Renames a thread in the index"""
    try:
        new_name = input(f"Enter new name for '{old_name}': ").strip()
        if not new_name:
            print("Rename cancelled.")
            return False
        
        threads = get_thread_index(client)
        if thread_id in threads:
            threads[thread_id] = new_name
            save_thread_index(client, threads)
            print(f"✓ Thread renamed to '{new_name}'.")
            return True
        return False
    except Exception as e:
        print(f"Error renaming thread: {e}")
        return False

def thread_management_menu(client, thread_id, thread_name):
    """Shows management options for a specific thread"""
    while True:
        print(f"\nManaging: '{thread_name}'")
        print(" [1] Rename thread")
        print(" [2] Delete thread")
        print(" [3] Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            if rename_thread(client, thread_id, thread_name):
                # Reload the main menu since name changed
                return "reload"
        elif choice == '2':
            confirm = input(f"Are you sure you want to delete '{thread_name}'? (yes/no): ").strip().lower()
            if confirm == 'yes':
                if delete_thread(client, thread_id, thread_name):
                    return "deleted"
        elif choice == '3':
            return "back"
        else:
            print("Invalid option.")

def thread_selection_menu(client):
    """Displays the interactive menu to select or create a chat thread"""
    while True:
        print("\n=========================================")
        print("      LOCAL LLM THREAD MANAGER")
        print("=========================================")
        
        # 1. Fetch current threads from the cluster
        threads = get_thread_index(client)
        
        if threads:
            print("\nExisting Threads:")
            # List them out numerically for easy selection
            thread_list = list(threads.items()) # contains [(id, name), (id, name)]
            for idx, (t_id, t_name) in enumerate(thread_list, 1):
                print(f" [{idx}] {t_name}")
            print(f" [N] Start a brand new thread")
            print(f" [M] Manage a thread (rename/delete)")
        else:
            print("\nNo existing threads found.")
            thread_list = []
            # No choice but to create a new one if DB is empty
        
        # 2. Process user menu choice
        choice = input("\nChoose an option or thread number: ").strip().lower()
        
        if choice == 'n' or not threads:
            # Create a brand new thread map entry
            name = input("Enter a meaningful name for this thread: ").strip()
            if not name:
                name = f"Untitled Thread ({uuid.uuid4().hex[:6]})"
            
            # Generate a truly unique ID for the Aerospike Record PK
            new_id = f"thread_{uuid.uuid4().hex[:12]}"
            threads[new_id] = name
            save_thread_index(client, threads)
            return new_id, name
        
        elif choice == 'm':
            if not thread_list:
                print("No threads to manage.")
                continue
            
            print("\nSelect thread to manage:")
            for idx, (t_id, t_name) in enumerate(thread_list, 1):
                print(f" [{idx}] {t_name}")
            
            manage_choice = input("\nSelect thread: ").strip()
            try:
                manage_idx = int(manage_choice) - 1
                if 0 <= manage_idx < len(thread_list):
                    manage_id, manage_name = thread_list[manage_idx]
                    result = thread_management_menu(client, manage_id, manage_name)
                    if result == "deleted":
                        continue  # Reload menu
                    elif result == "reload":
                        continue  # Reload menu
            except ValueError:
                print("Invalid selection.")
        
        else:
            try:
                selection_idx = int(choice) - 1
                if 0 <= selection_idx < len(thread_list):
                    selected_id, selected_name = thread_list[selection_idx]
                    return selected_id, selected_name
            except ValueError:
                pass
            
            print("Invalid selection. Please enter a valid number, 'N', or 'M'.")


def main():
    print("Connecting to your local Aerospike KV cluster...")
    client = get_aerospike_client()
    
    # Run the interactive thread menu
    active_thread_id, active_thread_name = thread_selection_menu(client)
    
    # Load history specific to this chosen thread
    chat_history = get_chat_history(client, active_thread_id)
    
    print(f"\n--- Entering Thread: '{active_thread_name}' ---")
    print(f"--- [Retrieved {len(chat_history)} past messages from Aerospike] ---")
    print("Type 'exit' or 'quit' to return to menu.\n")

    # Continuous chat loop
    while True:
        user_input = input("You: ")
        
        if user_input.strip().lower() in ['exit', 'quit']:
            print(f"\nExiting thread '{active_thread_name}'. Progress saved.")
            break
            
        if not user_input.strip():
            continue

        chat_history.append({"role": "user", "content": user_input})
        print("\nOllama: ", end="", flush=True)
        full_response = ""
        
        try:
            stream = ollama.chat(model="llama3", messages=chat_history, stream=True)
            for chunk in stream:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                full_response += content
            print("\n")
        except Exception as e:
            print(f"\nOllama streaming error: {e}\n")
            break

        chat_history.append({"role": "assistant", "content": full_response})
        
        # Save explicitly to the dynamically selected thread ID
        save_chat_history(client, active_thread_id, chat_history)

    client.close()

if __name__ == "__main__":
    main()
