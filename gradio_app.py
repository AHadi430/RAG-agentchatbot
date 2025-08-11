# import gradio as gr
# import uuid
# from rag_agent import (
#     load_document_and_build_retriever,
#     run_agent_with_query,
#     clear_session,
#     db  # MongoDB DB from your rag_agent.py
# )

# # Simulate a logged-in user (in real apps, replace this with auth logic)
# USER_ID = "demo_user"  # Fixed user for now

# def load_threads():
#     """Fetch thread IDs for current user."""
#     threads = db["session_docs"].find({"user_id": USER_ID})
#     return [doc["thread_id"] for doc in threads]

# def create_new_thread():
#     """Create new thread and return updated dropdown + status."""
#     thread_id = str(uuid.uuid4())
#     db["session_docs"].insert_one({
#         "user_id": USER_ID,
#         "thread_id": thread_id,
#         "document_name": None,
#         "document_summary": None
#     })
#     threads = load_threads()
#     return gr.update(choices=threads, value=thread_id), f"✅ New thread created: {thread_id[:8]}."

# def upload_pdf(file, thread_id):
#     """Upload PDF for a specific thread."""
#     if not thread_id:
#         return "⚠️ Please select a thread first."
#     load_document_and_build_retriever(file.name, user_id=USER_ID, thread_id=thread_id)
#     return "✅ Document uploaded successfully."

# def chatbot_response(message, chat_history, thread_id):
#     """Chat within selected thread."""
#     if not thread_id:
#         return "", chat_history, "⚠️ Please select a thread first."

#     response = run_agent_with_query(message, user_id=USER_ID, thread_id=thread_id) or ""
#     chat_history.append({"role": "user", "content": message})
#     chat_history.append({"role": "assistant", "content": response})
#     return "", chat_history, "✅ Response generated."

# def load_thread_history(thread_id):
#     """Load existing chat history for thread."""
#     chats = db["chat_history"].find({"user_id": USER_ID, "thread_id": thread_id}).sort("_id", 1)
#     history = []
#     for chat in chats:
#         history.append({"role": "user", "content": chat["query"]})
#         history.append({"role": "assistant", "content": chat["response"]})
#     return history, f"✅ Loaded history for {thread_id[:8]}."

# def reset_thread(thread_id):
#     """Clear a specific thread."""
#     if not thread_id:
#         return "⚠️ Select a thread first.", [], ""
#     clear_session(USER_ID, thread_id)
#     return f"✅ Thread {thread_id[:8]} reset.", [], ""

# with gr.Blocks(title="Multi-User Multi-Thread RAG Chatbot") as demo:
#     gr.Markdown("## 🤖 Multi-Thread Chatbot with Document RAG & Web Search")

#     with gr.Tabs():
#         with gr.Tab("📄 Document Upload"):
#             thread_selector = gr.Dropdown(label="Select Thread", choices=[], value=None)
#             new_thread_btn = gr.Button("➕ Create New Thread")
#             file_input = gr.File(label="Upload PDF", file_types=[".pdf"])
#             upload_btn = gr.Button("Upload Document")
#             upload_status = gr.Markdown()

#         with gr.Tab("💬 Chat"):
#             thread_selector_chat = gr.Dropdown(label="Select Thread", choices=[], value=None)
#             load_history_btn = gr.Button("🔄 Load History")
#             chatbot = gr.Chatbot(label="Chat", height=500, type="messages")
#             with gr.Row():
#                 message_input = gr.Textbox(placeholder="Type your message...", show_label=False, scale=4)
#                 send_btn = gr.Button("Send", variant="primary", scale=1)
#             reset_btn = gr.Button("🧹 Reset Thread", variant="secondary")
#             chat_status = gr.Markdown()

#     # Link thread dropdowns between tabs
#     def sync_threads():
#         threads = load_threads()
#         return gr.update(choices=threads), gr.update(choices=threads)

#     demo.load(sync_threads, inputs=[], outputs=[thread_selector, thread_selector_chat])

#     new_thread_btn.click(
#         fn=create_new_thread,
#         inputs=[],
#         outputs=[thread_selector, upload_status],
#     ).then(
#         fn=sync_threads, inputs=[], outputs=[thread_selector_chat, thread_selector]
#     )

#     upload_btn.click(
#         fn=upload_pdf,
#         inputs=[file_input, thread_selector],
#         outputs=[upload_status],
#     )

#     load_history_btn.click(
#         fn=load_thread_history,
#         inputs=[thread_selector_chat],
#         outputs=[chatbot, chat_status],
#     )

#     send_btn.click(
#         fn=chatbot_response,
#         inputs=[message_input, chatbot, thread_selector_chat],
#         outputs=[message_input, chatbot, chat_status],
#     )

#     reset_btn.click(
#         fn=reset_thread,
#         inputs=[thread_selector_chat],
#         outputs=[chat_status, chatbot, message_input],
#     )

# demo.launch()

import gradio as gr
import uuid
import inspect
from rag_agent import (
    load_document_and_build_retriever,
    run_agent_with_query,
    clear_session,
    db  # MongoDB DB from your rag_agent.py
)

# Simulate a logged-in user (in real apps, replace this with auth logic)
USER_ID = "demo_user"  # Fixed user for now




def load_threads():
    """Fetch thread IDs for current user."""
    threads = db["session_docs"].find({"user_id": USER_ID})
    return [doc["thread_id"] for doc in threads]


def create_new_thread():
    """Create new thread and return updated dropdown + status."""
    thread_id = str(uuid.uuid4())
    db["session_docs"].insert_one({
        "user_id": USER_ID,
        "thread_id": thread_id,
        "document_name": None,
        "document_summary": None
    })
    threads = load_threads()
    return gr.update(choices=threads, value=thread_id), f"✅ New thread created: {thread_id[:8]}."


def upload_pdf(file, thread_id):
    """Upload PDF for a specific thread."""
    if not thread_id:
        return "⚠️ Please select a thread first."
    load_document_and_build_retriever(file.name, user_id=USER_ID, thread_id=thread_id)
    return "✅ Document uploaded successfully."


def chatbot_response(message, chat_history, thread_id):
    """Chat within selected thread."""
    if not thread_id:
        return "", chat_history, "⚠️ Please select a thread first."
    response = run_agent_with_query(message, user_id=USER_ID, thread_id=thread_id) or ""
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": response})
    return "", chat_history, "✅ Response generated."


def load_thread_history(thread_id):
    """Load existing chat history for thread."""
    chats = db["chat_history"].find({"user_id": USER_ID, "thread_id": thread_id}).sort("_id", 1)
    history = []
    for chat in chats:
        history.append({"role": "user", "content": chat["query"]})
        history.append({"role": "assistant", "content": chat["response"]})
    return history, f"✅ Loaded history for {thread_id[:8]}."


def reset_thread(thread_id):
    """Clear a specific thread."""
    if not thread_id:
        return "⚠️ Select a thread first.", [], ""
    clear_session(USER_ID, thread_id)
    return f"✅ Thread {thread_id[:8]} reset.", [], ""


def sync_threads():
    threads = load_threads()
    return gr.update(choices=threads), gr.update(choices=threads)


with gr.Blocks(title="Multi-User Multi-Thread RAG Chatbot") as demo:
    gr.Markdown("## 🤖 Multi-Thread Chatbot with Document RAG & Web Search")

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

    # Link thread dropdowns between tabs
    def sync_threads():
        threads = load_threads()
        return gr.update(choices=threads), gr.update(choices=threads)

    demo.load(sync_threads, inputs=[], outputs=[thread_selector, thread_selector_chat])

    new_thread_btn.click(
        fn=create_new_thread,
        inputs=[],
        outputs=[thread_selector, upload_status],
    ).then(
        fn=sync_threads, inputs=[], outputs=[thread_selector_chat, thread_selector]
    )

    upload_btn.click(
        fn=upload_pdf,
        inputs=[file_input, thread_selector],
        outputs=[upload_status],
    )

    load_history_btn.click(
        fn=load_thread_history,
        inputs=[thread_selector_chat],
        outputs=[chatbot, chat_status],
    )

    send_btn.click(
        fn=chatbot_response,
        inputs=[message_input, chatbot, thread_selector_chat],
        outputs=[message_input, chatbot, chat_status],
    )

    reset_btn.click(
        fn=reset_thread,
        inputs=[thread_selector_chat],
        outputs=[chat_status, chatbot, message_input],
    )

demo.launch()
