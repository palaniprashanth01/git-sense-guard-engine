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

def get_llm():
    api_key = get_current_api_key()
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        api_key=api_key
    )

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
DB_DIR = "./chroma_db"

def get_vector_store(repo_id: str):
    return Chroma(
        collection_name=repo_id,
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

def run_with_retry(chain_creation_func, query, max_retries=3):
    """Executes a chain with API key rotation on failure."""
    global current_key_index
    attempts = 0
    
    while attempts < max_retries:
        try:
            # Create fresh LLM and chain with current key
            llm = get_llm()
            qa_chain = chain_creation_func(llm)
            result = qa_chain.invoke(query)
            return result["result"]
        except Exception as e:
            error_str = str(e).lower()
            # Check for rate limit (429) or auth error (401)
            if "429" in error_str or "rate limit" in error_str or "401" in error_str:
                print(f"API Error ({e}). Rotating key and retrying...")
                rotate_api_key()
                attempts += 1
                time.sleep(1) # Brief pause
            else:
                raise e
    
    raise Exception("Max retries exceeded. All API keys might be exhausted.")

def analyze_bugs(repo_id: str):
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10}) # Reduced from 20 to 10
    
    prompt_template = """
    You are an expert code security and quality analyzer.
    Analyze the following code snippets from a repository.
    Identify potential security vulnerabilities (e.g., XSS, SQL injection, hardcoded secrets) and major logical bugs.
    
    Context:
    {context}
    
    For each issue found, provide:
    1. The file name (if available in context).
    2. The line number (approximate).
    3. A description of the issue.
    4. Severity (High/Medium/Low).
    
    **CRITICAL INSTRUCTIONS:**
    - Output MUST be a valid JSON list of objects.
    - Keys: "file", "line", "description", "severity".
    - Do NOT include markdown formatting (no ```json).
    - If no issues are found, return [].
    - Limit to the top 10 most critical issues to avoid response truncation.
    - Ensure the JSON is well-formed and closed properly.
    """
    
    def create_chain(llm):
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PromptTemplate(template=prompt_template, input_variables=["context"])}
        )
    
    return run_with_retry(create_chain, "Find security vulnerabilities, bugs, and errors in the code.")

def analyze_suggestions(repo_id: str):
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5}) # Reduced from 10 to 5
    
    prompt_template = """
    You are a senior software engineer.
    Analyze the following code snippets.
    Identify areas for architecture improvement, code quality, and refactoring.
    Focus on readability, performance, and maintainability.
    
    Context:
    {context}
    
    **CRITICAL INSTRUCTIONS:**
    - Output ONLY a valid JSON list of objects.
    - NO introductory text. NO markdown formatting.
    - Start the response with '[' and end with ']'.
    - Keys: "file", "description", "suggestion".
    - Limit to the top 5 most impactful suggestions.
    - Ensure the JSON is well-formed.
    """
    
    def create_chain(llm):
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PromptTemplate(template=prompt_template, input_variables=["context"])}
        )
    
    return run_with_retry(create_chain, "Identify code quality improvements and refactoring opportunities.")

def generate_readme(repo_id: str):
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5}) # Reduced from 10 to 5
    
    prompt_template = """
    You are a technical writer.
    Based on the following code snippets, generate a comprehensive README.md file.
    Include sections: Introduction, Features, Tech Stack, and Installation (inferred).
    
    Context:
    {context}
    
    Output the README content in Markdown format.
    """
    
    def create_chain(llm):
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PromptTemplate(template=prompt_template, input_variables=["context"])}
        )
    
    return run_with_retry(create_chain, "Generate a README.md for this project.")

def analyze_structure(repo_id: str, file_tree: str = ""):
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10}) # Reduced from 20 to 10
    
    # Truncate file tree if it's too long (approx 2000 chars)
    if len(file_tree) > 2000:
        file_tree = file_tree[:2000] + "\n... (truncated)"
    
    prompt_template = """
    You are a software architect.
    Based on the provided code snippets and the user's question (which may contain the file tree), describe the high-level structure and architecture of the repository.
    
    **Instructions:**
    - Use a clear, bullet-point format.
    - Group files by their role (e.g., **Data**, **Model**, **Utils**).
    - Explain the flow of data or execution briefly.
    - Keep it concise and easy to read.
    - Do NOT just list files; explain their purpose.
    
    Context:
    {context}
    
    Question: {question}
    
    Output the description in Markdown format.
    """
    
    question = f"Describe the repository structure and architecture. Here is the file tree:\n{file_tree}"
    
    def create_chain(llm):
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PromptTemplate(template=prompt_template, input_variables=["context", "question"])}
        )
    
    result_text = run_with_retry(create_chain, {"query": question})
    
    # Append the raw file tree to the output
    return result_text + "\n\n## File Tree\n```text\n" + file_tree + "\n```"

def analyze_file_summaries(repo_id: str):
    vector_store = get_vector_store(repo_id)
    retriever = vector_store.as_retriever(search_kwargs={"k": 10}) # Reduced from 20 to 10
    
    prompt_template = """
    You are a code analyst.
    Based on the provided code snippets, identify the most important files and provide a one-sentence summary for each.
    
    Context:
    {context}
    
    **CRITICAL INSTRUCTIONS:**
    - Output ONLY a valid JSON list of objects.
    - NO introductory text. NO markdown formatting.
    - Start the response with '[' and end with ']'.
    - Keys: "file", "summary".
    - Limit to the top 15 files.
    - Ensure the JSON is well-formed.
    """
    
    def create_chain(llm):
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PromptTemplate(template=prompt_template, input_variables=["context"])}
        )
    
    return run_with_retry(create_chain, "Summarize key files in the repository.")
