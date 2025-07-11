from fastapi import FastAPI, UploadFile, Form
from typing import List
import shutil
import os
import uuid
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from rag_agent import (
    load_document_and_build_retriever,
    run_agent_with_query,
    clear_session,
    db
)

USER_ID = "demo_user"  # Simulate logged-in user
app = FastAPI(title="Multi-Thread RAG Chatbot")

@app.get("/threads")
def list_threads():
    """List all threads of the current user."""
    threads = db["session_docs"].find({"user_id": USER_ID})
    return [doc["thread_id"] for doc in threads]

@app.post("/threads/new")
def create_thread():
    """Create a new chat thread."""
    thread_id = str(uuid.uuid4())
    db["session_docs"].insert_one({
        "user_id": USER_ID,
        "thread_id": thread_id,
        "document_name": None,
        "document_summary": None
    })
    return {"thread_id": thread_id}

@app.post("/upload")
async def upload_document(file: UploadFile, thread_id: str = Form(...)):
    """Upload PDF and process it."""
    try:
        # Read the file contents
        contents = await file.read()
        
        # Create a proper temporary file path using the original filename
        # Extract just the filename without the full path
        original_filename = os.path.basename(file.filename) if file.filename else "uploaded_file.pdf"
        save_path = f"temp_{original_filename}"
        
        # Write the contents to the temporary file
        with open(save_path, "wb") as f:
            f.write(contents)
        
        # Process the document
        load_document_and_build_retriever(save_path, user_id=USER_ID, thread_id=thread_id)
        
        # Clean up the temporary file
        if os.path.exists(save_path):
            os.remove(save_path)
            
        return {"status": "✅ Document uploaded and processed successfully."}
    
    except Exception as e:
        # Clean up temporary file in case of error
        if 'save_path' in locals() and os.path.exists(save_path):
            os.remove(save_path)
        return {"status": f"❌ Upload failed: {str(e)}"}

@app.post("/chat")
def chat(query: str = Form(...), thread_id: str = Form(...)):
    """Chat in a thread."""
    if not thread_id:
        return {"error": "Thread ID required."}
    answer = run_agent_with_query(query, USER_ID, thread_id)
    return {"response": answer}

@app.get("/threads/{thread_id}/history")
def get_thread_history(thread_id: str):
    """Fetch chat history of thread."""
    chats = db["chat_history"].find({"user_id": USER_ID, "thread_id": thread_id}).sort("_id", 1)
    history = []
    for chat in chats:
        history.append({"role": "user", "content": chat["query"]})
        history.append({"role": "assistant", "content": chat["response"]})
    return history

@app.post("/threads/{thread_id}/reset")
def reset_thread(thread_id: str):
    """Clear chat history & doc of thread."""
    clear_session(USER_ID, thread_id)
    return {"status": "Thread reset."}