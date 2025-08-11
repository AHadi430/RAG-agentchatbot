import gradio as gr
import requests
import os

BACKEND_URL = "http://127.0.0.1:8000"  

def get_threads():
    """Fetch all threads."""
    res = requests.get(f"{BACKEND_URL}/threads")
    return res.json()

def create_thread():
    """Create a new thread and update dropdown."""
    res = requests.post(f"{BACKEND_URL}/threads/new")
    thread_id = res.json().get("thread_id")
    threads = get_threads()
    return gr.update(choices=threads, value=thread_id), f"✅ New thread created: {thread_id[:8]}"

def upload_pdf(file, thread_id):
    """Correct file upload via FastAPI."""
    if not thread_id:
        return "⚠️ Please select a thread first."
    
    if not file:
        return "⚠️ Please select a file to upload."

    try:
        # Use the actual file path that Gradio provides
        with open(file, "rb") as f:
            # Extract just the filename for the form data
            filename = os.path.basename(file)
            files = {'file': (filename, f, 'application/pdf')}
            data = {'thread_id': thread_id}
            res = requests.post("http://localhost:8000/upload", files=files, data=data)

        return res.json().get("status", "❌ Upload failed.")
    
    except Exception as e:
        return f"❌ Upload failed: {str(e)}"

def chat_with_agent(message, chat_history, thread_id):
    """Send message to backend."""
    if not thread_id:
        return "", chat_history, "⚠️ Please select a thread first."
    res = requests.post(
        f"{BACKEND_URL}/chat",
        data={"query": message, "thread_id": thread_id}
    )
    response = res.json().get("response", "❌ Error from backend.")
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": response})
    return "", chat_history, "✅ Response generated."

def load_history(thread_id):
    """Load chat history."""
    res = requests.get(f"{BACKEND_URL}/threads/{thread_id}/history")
    history = res.json()
    return history, f"✅ History loaded for {thread_id[:8]}"

def reset_thread(thread_id):
    """Clear chat history & document."""
    if not thread_id:
        return "⚠️ Please select a thread.", [], None
    requests.post(f"{BACKEND_URL}/threads/{thread_id}/reset")
    return f"✅ Thread {thread_id[:8]} reset.", [], None

with gr.Blocks(title="Gradio Frontend for FastAPI RAG Chatbot") as demo:
    gr.Markdown("## 🤖 RAG Chatbot (Gradio + FastAPI Backend)")

    with gr.Tabs():
        with gr.Tab("📄 Document Upload"):
            thread_selector = gr.Dropdown(label="Select Thread", choices=[], value=None)
            new_thread_btn = gr.Button("➕ Create New Thread")
            file_input = gr.File(label="Upload PDF", file_types=[".pdf"])
            upload_btn = gr.Button("Upload Document")
            upload_status = gr.Markdown()

        with gr.Tab("💬 Chat"):
            thread_selector_chat = gr.Dropdown(label="Select Thread", choices=[], value=None)
            load_history_btn = gr.Button("🔄 Load History")
            chatbot = gr.Chatbot(label="Chat", height=500, type="messages")
            with gr.Row():
                message_input = gr.Textbox(placeholder="Type your message...", show_label=False, scale=4)
                send_btn = gr.Button("Send", variant="primary", scale=1)
            reset_btn = gr.Button("🧹 Reset Thread", variant="secondary")
            chat_status = gr.Markdown()

    # Sync thread dropdowns on load
    def sync_threads():
        threads = get_threads()
        return gr.update(choices=threads), gr.update(choices=threads)

    demo.load(sync_threads, inputs=[], outputs=[thread_selector, thread_selector_chat])

    new_thread_btn.click(
        fn=create_thread,
        inputs=[],
        outputs=[thread_selector, upload_status],
    ).then(
        fn=sync_threads, inputs=[], outputs=[thread_selector, thread_selector_chat]
    )

    upload_btn.click(
        fn=upload_pdf,
        inputs=[file_input, thread_selector],
        outputs=[upload_status],
    )

    load_history_btn.click(
        fn=load_history,
        inputs=[thread_selector_chat],
        outputs=[chatbot, chat_status],
    )

    send_btn.click(
        fn=chat_with_agent,
        inputs=[message_input, chatbot, thread_selector_chat],
        outputs=[message_input, chatbot, chat_status],
    )

    reset_btn.click(
        fn=reset_thread,
        inputs=[thread_selector_chat],
        outputs=[chat_status, chatbot, message_input],
    )

demo.launch()
