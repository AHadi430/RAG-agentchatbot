import os
import pymongo
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from operator import add as add_messages
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.tools import tool
from groq import Groq
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# MongoDB setup
MONGO_URI = os.getenv("MONGODB_URI")
mongo = pymongo.MongoClient(MONGO_URI)
db = mongo["Rag_Agent"]
vec_coll = db["vector_store"]
chat_coll = db["chat_history"]

# LLM & Web Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

retriever = None  # Global per-thread retriever (in production, you'd isolate better)

def summarize_document(pages):
    """Summarize first few pages."""
    return " ".join(" ".join(p.page_content.split()[:50]) for p in pages[:3])

@tool
def retriever_tool(query: str) -> str:
    """Retrieve document excerpts."""
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant document info found."
    return "\n\n".join(f"Excerpt {i+1}: {doc.page_content}" for i, doc in enumerate(docs))

tools = [retriever_tool]
tools_dict = {t.name: t for t in tools}

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def should_continue(state: AgentState):
    return hasattr(state['messages'][-1], 'tool_calls') and state['messages'][-1].tool_calls

def groq_llm(prompt: str) -> str:
    """Call Groq LLM."""
    chat = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content

def call_llm(state: AgentState) -> AgentState:
    """LLM Reasoning."""
    human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
    query = human.content if human else ""

    doc_text = "\n\n".join(m.content for m in state["messages"]
                           if isinstance(m, ToolMessage) and m.name == "retriever_tool")
    memory = "\n".join(
        f"User: {m.content}" if isinstance(m, HumanMessage) else f"AI: {m.content}"
        for m in state["messages"][:-1]
        if isinstance(m, (HumanMessage, AIMessage))
    )

    base = f"{memory}\n\n"
    if doc_text:
        base += f"Document Excerpts:\n{doc_text}\n\n"
    base += f"Question: {query}\nAnswer with sources."

    resp = groq_llm(base)
    return {"messages": state["messages"] + [AIMessage(content=resp)]}

def take_action(state: AgentState) -> AgentState:
    """Execute tools."""
    msgs = state["messages"].copy()
    for call in state["messages"][-1].tool_calls:
        res = tools_dict[call.name].invoke(call.args["query"])
        msgs.append(ToolMessage(tool_call_id=call.id, name=call.name, content=res))
    return {"messages": msgs}

graph = StateGraph(AgentState)
graph.add_node("llm", call_llm)
graph.add_node("tool", take_action)
graph.add_conditional_edges("llm", should_continue, {True: "tool", False: END})
graph.add_edge("tool", "llm")
graph.set_entry_point("llm")
rag_agent = graph.compile()

def run_agent_with_query(query: str, user_id: str, thread_id: str):
    """Agent with multi-user & multi-thread chat support, with natural responses."""
    document_name, document_summary = get_document_context(user_id, thread_id)
    recent_chats = list(chat_coll.find({"user_id": user_id, "thread_id": thread_id}).sort("_id", -1).limit(5))
    recent_chats = list(reversed(recent_chats))

    messages = []
    for chat in recent_chats:
        messages.append(HumanMessage(content=chat["query"]))
        messages.append(AIMessage(content=chat["response"]))
    messages.append(HumanMessage(content=query))

    web_result = None
    if force_web_search_if_needed(query):
        print("[INFO] Auto-fetching web search results...")
        web_result = web_search_tool(query)

    memory = "\n".join(
        f"User: {m.content}" if isinstance(m, HumanMessage) else f"AI: {m.content}"
        for m in messages[:-1]
        if isinstance(m, (HumanMessage, AIMessage))
    )

    prompt = f"{memory}\n\n"
    if document_name:
        prompt += f"Document: {document_name}\nSummary:\n{document_summary}\n\n"
    if web_result:
        prompt += f"Web Search Results:\n{web_result}\n\n"

    prompt += f"Question: {query}\n"

    if document_name or web_result:
        prompt += "Answer with sources if applicable."
    else:
        prompt += "Answer concisely and naturally. No need for sources or extra formalities."

    answer = groq_llm(prompt)

    chat_coll.insert_one({
        "user_id": user_id,
        "thread_id": thread_id,
        "query": query,
        "response": answer
    })

    return ""  # or a string, dict, or list as appropriate

def web_search_tool(query: str) -> str:
    """Live web search using Tavily."""
    resp = tavily_client.search(query=query, max_results=3, search_depth="advanced")
    results = resp.get("results", [])
    if not results:
        return "No web search results found."
    return "\n\n".join(f"{r['title']}\n{r['url']}\n{r['content']}" for r in results)

def force_web_search_if_needed(query: str) -> bool:
    """Detect if web search needed."""
    keywords = ["latest", "recent", "today", "breaking", "news", "result", "match", "score", "live", "date", "current", "happening", "won", "win", "now"]
    return any(k in query.lower() for k in keywords)

def load_document_and_build_retriever(pdf_path: str, user_id: str, thread_id: str):
    """Load PDF, store vectors per user & thread."""
    global retriever
    document_name = os.path.basename(pdf_path)
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    document_summary = summarize_document(pages)

    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(pages)

    vectorstore = MongoDBAtlasVectorSearch.from_documents(
        documents=splits,
        embedding=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
        collection=vec_coll,
        index_name="default"
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    db["session_docs"].update_one(
        {"user_id": user_id, "thread_id": thread_id},
        {"$set": {"document_name": document_name, "document_summary": document_summary}},
        upsert=True
    )

def get_document_context(user_id: str, thread_id: str):
    """Get doc summary for chat."""
    doc = db["session_docs"].find_one({"user_id": user_id, "thread_id": thread_id})
    if doc:
        return doc["document_name"], doc["document_summary"]
    return None, None

def clear_session(user_id: str, thread_id: str):
    """Clear chat & doc."""
    chat_coll.delete_many({"user_id": user_id, "thread_id": thread_id})
    db["session_docs"].delete_one({"user_id": user_id, "thread_id": thread_id})
