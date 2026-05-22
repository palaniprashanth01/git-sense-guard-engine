from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.chains import RetrievalQA
import os
import time
from dotenv import load_dotenv

load_dotenv()

import random

# API Key Rotation Logic
api_keys_str = os.getenv("GROQ_API_KEYS", "")
API_KEYS = [k.strip() for k in api_keys_str.split(",") if k.strip()]
# Randomize start index to avoid hammering the first key on restarts
current_key_index = random.randint(0, len(API_KEYS) - 1) if API_KEYS else 0
print(f"Initialized with API Key Index: {current_key_index} (Total Keys: {len(API_KEYS)})")

def get_current_api_key():
    global current_key_index
    if not API_KEYS:
        raise ValueError("No GROQ_API_KEYS found in .env")
    return API_KEYS[current_key_index]

def rotate_api_key():
    global current_key_index
    if not API_KEYS:
        return
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    print(f"Rotating API Key. New index: {current_key_index}")

def get_llm(json_mode: bool = False):
    api_key = get_current_api_key()
    kwargs = {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.2,
        "api_key": api_key
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return ChatGroq(**kwargs)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
DB_DIR = "./chroma_db"

def get_vector_store(repo_id: str):
    return Chroma(
        collection_name=repo_id,
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

def run_llm_direct(prompt: str, json_mode: bool = False, max_retries: int = 3) -> str:
    """Executes a direct LLM call with API key rotation on rate limits."""
    global current_key_index
    attempts = 0
    while attempts < max_retries:
        try:
            llm = get_llm(json_mode=json_mode)
            res = llm.invoke(prompt)
            return res.content
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "401" in error_str:
                print(f"API Error ({e}). Rotating key and retrying...")
                rotate_api_key()
                attempts += 1
                time.sleep(1) # Brief pause
            else:
                raise e
    raise Exception("Max retries exceeded. All API keys might be exhausted.")

def analyze_bugs(repo_id: str) -> str:
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    docs = retriever.invoke("Find security vulnerabilities, bugs, and errors in the code.")
    context = "\n\n".join([f"--- File: {d.metadata.get('source', 'unknown')} ---\n{d.page_content}" for d in docs])
    
    prompt = f"""You are an expert code security and quality analyzer.
Analyze the following code snippets from a repository.
Identify potential security vulnerabilities (e.g., XSS, SQL injection, hardcoded secrets) and major logical bugs.

Context:
{context}

Return a JSON object with a "bugs" key containing a list of security vulnerabilities and bugs.
Each bug object in the list MUST have the keys: "file", "line", "description", "severity".

CRITICAL INSTRUCTIONS:
1. Your entire response MUST be a single, valid JSON object with the key "bugs".
2. Do NOT wrap the JSON in markdown code blocks or add any markdown formatting.
3. Keep the severity strictly as one of: "High", "Medium", "Low".
4. Limit to the top 10 most critical issues.
5. If no issues are found, the "bugs" list should be empty.

Example structure:
{{
  "bugs": [
    {{
      "file": "app/views.py",
      "line": 12,
      "description": "Hardcoded API key detected.",
      "severity": "High"
    }}
  ]
}}
"""
    return run_llm_direct(prompt, json_mode=True)

def analyze_suggestions(repo_id: str) -> str:
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke("Identify code quality improvements and refactoring opportunities.")
    context = "\n\n".join([f"--- File: {d.metadata.get('source', 'unknown')} ---\n{d.page_content}" for d in docs])
    
    prompt = f"""You are a senior software engineer.
Analyze the following code snippets.
Identify areas for architecture improvement, code quality, and refactoring. Focus on readability, performance, and maintainability.

Context:
{context}

Return a JSON object with a "suggestions" key containing a list of code quality and refactoring recommendations.
Each suggestion object in the list MUST have the keys: "file", "description", "suggestion".

CRITICAL INSTRUCTIONS:
1. Your entire response MUST be a single, valid JSON object with the key "suggestions".
2. Do NOT wrap the JSON in markdown code blocks or add any markdown formatting.
3. Limit to the top 5 most impactful suggestions.

Example structure:
{{
  "suggestions": [
    {{
      "file": "utils.py",
      "description": "Nested loops are causing O(N^2) complexity.",
      "suggestion": "Refactor nested loops using a hash map lookup."
    }}
  ]
}}
"""
    return run_llm_direct(prompt, json_mode=True)

def generate_readme(repo_id: str) -> str:
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke("Generate a README.md for this project.")
    context = "\n\n".join([f"--- File: {d.metadata.get('source', 'unknown')} ---\n{d.page_content}" for d in docs])
    
    prompt = f"""You are a technical writer.
Based on the following code snippets, generate a comprehensive README.md file.
Include sections: Introduction, Features, Tech Stack, and Installation (inferred).

Context:
{context}

Output the README content in Markdown format.
"""
    return run_llm_direct(prompt)

def analyze_structure(repo_id: str, file_tree: str = "") -> str:
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    
    if len(file_tree) > 2000:
        file_tree = file_tree[:2000] + "\n... (truncated)"
        
    docs = retriever.invoke(f"Describe the repository structure and architecture. File tree:\n{file_tree}")
    context = "\n\n".join([f"--- File: {d.metadata.get('source', 'unknown')} ---\n{d.page_content}" for d in docs])
    
    prompt = f"""You are a software architect.
Based on the provided code snippets and the file tree, describe the high-level structure and architecture of the repository.

Context:
{context}

File Tree:
{file_tree}

Instructions:
1. Use a clear, bullet-point format.
2. Group files by their role (e.g., **Data**, **Model**, **Utils**).
3. Explain the flow of data or execution briefly.
4. Keep it concise and easy to read.
5. Do NOT just list files; explain their purpose.

Output the description in Markdown format.
"""
    result_text = run_llm_direct(prompt)
    return result_text + "\n\n## File Tree\n```text\n" + file_tree + "\n```"

def analyze_file_summaries(repo_id: str) -> str:
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    docs = retriever.invoke("Summarize key files in the repository.")
    context = "\n\n".join([f"--- File: {d.metadata.get('source', 'unknown')} ---\n{d.page_content}" for d in docs])
    
    prompt = f"""You are a code analyst.
Based on the provided code snippets, identify the most important files and provide a one-sentence summary for each.

Context:
{context}

Return a JSON object with a "file_summaries" key containing a list of file summaries.
Each summary object in the list MUST have the keys: "file", "summary".

CRITICAL INSTRUCTIONS:
1. Your entire response MUST be a single, valid JSON object with the key "file_summaries".
2. Do NOT wrap the JSON in markdown code blocks or add any markdown formatting.
3. Limit to the top 15 files.

Example structure:
{{
  "file_summaries": [
    {{
      "file": "app.py",
      "summary": "Main entry point of the Gradio interface that sets up page routing and layout."
    }}
  ]
}}
"""
    return run_llm_direct(prompt, json_mode=True)

