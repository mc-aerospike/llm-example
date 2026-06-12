import atexit
from flask import Flask, render_template, request, redirect, url_for, flash
from app_llm import (
    get_aerospike_client,
    get_thread_index,
    create_thread,
    set_thread_name,
    delete_thread,
    get_chat_history,
    save_chat_history,
)
import ollama

app = Flask(__name__)
app.secret_key = "change-this-secret"

client = get_aerospike_client()

def get_thread_list():
    return list(get_thread_index(client).items())

@app.route("/")
def index():
    threads = get_thread_list()
    return render_template("index.html", threads=threads)

@app.route("/thread", methods=["POST"])
def new_thread():
    name = request.form.get("thread_name", "").strip()
    thread_id, thread_name = create_thread(client, name)
    flash(f"Thread '{thread_name}' created.")
    return redirect(url_for("view_thread", thread_id=thread_id))

@app.route("/thread/<thread_id>")
def view_thread(thread_id):
    threads = dict(get_thread_list())
    thread_name = threads.get(thread_id)
    if thread_name is None:
        flash("Thread not found.")
        return redirect(url_for("index"))

    messages = get_chat_history(client, thread_id)
    return render_template(
        "thread.html",
        threads=threads.items(),
        thread_id=thread_id,
        thread_name=thread_name,
        messages=messages,
    )

@app.route("/thread/<thread_id>/reload")
def reload_thread(thread_id):
    return redirect(url_for("view_thread", thread_id=thread_id))

@app.route("/thread/<thread_id>/message", methods=["POST"])
def send_message(thread_id):
    user_message = request.form.get("message", "").strip()
    if not user_message:
        flash("Enter a message before sending.")
        return redirect(url_for("view_thread", thread_id=thread_id))

    messages = get_chat_history(client, thread_id)
    messages.append({"role": "user", "content": user_message})

    try:
        stream = ollama.chat(model="llama3", messages=messages, stream=True)
        assistant_response = ""
        for chunk in stream:
            assistant_response += chunk["message"]["content"]
    except Exception as exc:
        flash(f"LLM error: {exc}")
        return redirect(url_for("view_thread", thread_id=thread_id))

    messages.append({"role": "assistant", "content": assistant_response})
    save_chat_history(client, thread_id, messages)
    return redirect(url_for("view_thread", thread_id=thread_id))

@app.route("/thread/<thread_id>/rename", methods=["POST"])
def rename_thread_route(thread_id):
    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        flash("Please provide a new thread name.")
    elif set_thread_name(client, thread_id, new_name):
        flash("Thread renamed successfully.")
    else:
        flash("Thread rename failed.")
    return redirect(url_for("view_thread", thread_id=thread_id))

@app.route("/thread/<thread_id>/delete", methods=["POST"])
def delete_thread_route(thread_id):
    threads = dict(get_thread_list())
    thread_name = threads.get(thread_id, "Unknown Thread")
    if delete_thread(client, thread_id, thread_name):
        flash(f"Thread '{thread_name}' deleted.")
        return redirect(url_for("index"))
    flash("Thread deletion failed.")
    return redirect(url_for("view_thread", thread_id=thread_id))

@atexit.register
def cleanup_client():
    try:
        client.close()
    except Exception:
        pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
