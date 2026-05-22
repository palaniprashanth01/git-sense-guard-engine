import os
import shutil
import tempfile
from git import Repo
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Initialize Embeddings
# Using local HuggingFace model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

DB_DIR = "./chroma_db"

def get_repo_id(repo_url: str) -> str:
    """Extracts and sanitizes repo_id from URL."""
    # Extract basename
    repo_id = repo_url.split("/")[-1].replace(".git", "")
    # Remove trailing non-alphanumeric characters (to satisfy ChromaDB constraints)
    while repo_id and not repo_id[-1].isalnum():
        repo_id = repo_id[:-1]
    return repo_id

def clone_repository(repo_url: str, branch: str = None) -> str:
    """Clones the repository to a temporary directory."""
    temp_dir = tempfile.mkdtemp()
    print(f"Cloning {repo_url} to {temp_dir}...")
    try:
        if branch:
            Repo.clone_from(repo_url, temp_dir, branch=branch)
        else:
            Repo.clone_from(repo_url, temp_dir)
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir)
        raise e

def load_and_process_files(repo_path: str) -> list[Document]:
    """Loads code files and splits them into chunks."""
    print("Loading files...")
    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*",
        suffixes=[".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".h", ".c", ".md"],
        parser=LanguageParser()
    )
    documents = loader.load()
    
    print(f"Loaded {len(documents)} documents.")
    
    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language="python", # Defaulting to python for splitting logic, but works generally
        chunk_size=2000,
        chunk_overlap=200
    )
    texts = text_splitter.split_documents(documents)
    print(f"Split into {len(texts)} chunks.")
    return texts

def index_documents(documents: list[Document], repo_id: str):
    """Indexes documents into ChromaDB."""
    print(f"Indexing {len(documents)} chunks for repo {repo_id}...")
    
    # We use a separate collection for each repo or filter by metadata
    # For simplicity, let's use a single collection and filter by repo_id if needed,
    # or just create a persistent client.
    
    vector_store = Chroma(
        collection_name=repo_id,
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )
    
    vector_store.add_documents(documents)
    print("Indexing complete.")
    return vector_store

def generate_file_tree(startpath: str) -> str:
    """Generates a text-based file tree."""
    tree = []
    for root, dirs, files in os.walk(startpath):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        
        # Don't print the root temp dir name, just start from its contents or use "/"
        if root == startpath:
            tree.append("/")
        else:
            tree.append(f"{indent}{os.path.basename(root)}/")
            
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree.append(f"{subindent}{f}")
    return "\n".join(tree)

def process_repository(repo_url: str, branch: str = None) -> tuple[str, str]:
    """Full pipeline: Clone -> Load -> Split -> Index. Returns (repo_id, file_tree)."""
    repo_id = get_repo_id(repo_url)
    
    temp_dir = clone_repository(repo_url, branch)
    try:
        # Generate file tree before processing
        file_tree = generate_file_tree(temp_dir)
        
        documents = load_and_process_files(temp_dir)
        # Add repo_id to metadata
        for doc in documents:
            doc.metadata["repo_id"] = repo_id
            doc.metadata["source"] = doc.metadata["source"].replace(temp_dir, "") # Relative path
            
        index_documents(documents, repo_id)
        return repo_id, file_tree
    finally:
        shutil.rmtree(temp_dir)

def get_recent_commits(repo_url: str, limit: int = 10) -> list[dict]:
    """Retrieves recent commits from the repository."""
    temp_dir = clone_repository(repo_url)
    try:
        repo = Repo(temp_dir)
        commits = []
        for commit in list(repo.iter_commits(max_count=limit)):
            commits.append({
                "hash": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat()
            })
        return commits
    finally:
        shutil.rmtree(temp_dir)
