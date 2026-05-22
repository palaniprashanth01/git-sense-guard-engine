from dataclasses import asdict

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AnalyzeRequest, AnalysisResponse, AuditRequest, AuditResponse, PushRequest
import agents
import ingestion
import analysis
import git_utils
import json
import re
import ast
import asyncio
import os

app = FastAPI(title="Git Sense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for results (replace with DB in production)
results_store = {}

def clean_json_string(json_str: str) -> str:
    """Removes markdown code blocks and extracts JSON."""
    print(f"DEBUG: Raw JSON string length: {len(json_str)}")
    
    # Try to find JSON block in markdown
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    matches = re.findall(pattern, json_str, re.DOTALL)
    if matches:
        # Take the longest match which is likely the main content
        json_str = max(matches, key=len)
    
    # Prioritize outer-most object {} or list [] depending on what appears first
    start_list = json_str.find("[")
    start_obj = json_str.find("{")
    
    if start_obj != -1 and (start_list == -1 or start_obj < start_list):
        # We have an object starting before a list, or no list at all
        end_obj = json_str.rfind("}")
        if end_obj != -1:
            return json_str[start_obj : end_obj + 1]
            
    if start_list != -1:
        # We have a list
        end_list = json_str.rfind("]")
        if end_list != -1:
            return json_str[start_list : end_list + 1]
            
    # Fallback to single objects if still not matched
    if start_obj != -1:
        end_obj = json_str.rfind("}")
        if end_obj != -1:
            return json_str[start_obj : end_obj + 1]

    return json_str.strip()

def parse_json_safely(json_str: str):
    """Tries to parse JSON, falling back to ast.literal_eval. Handles key extraction from dicts."""
    cleaned = clean_json_string(json_str)
    try:
        parsed = json.loads(cleaned, strict=False)
        if isinstance(parsed, dict):
            for k in ["bugs", "suggestions", "file_summaries"]:
                if k in parsed and isinstance(parsed[k], list):
                    return parsed[k]
        return parsed
    except json.JSONDecodeError:
        try:
            # Fallback for Python-style dicts/lists (single quotes)
            parsed = ast.literal_eval(cleaned)
            if isinstance(parsed, dict):
                for k in ["bugs", "suggestions", "file_summaries"]:
                    if k in parsed and isinstance(parsed[k], list):
                        return parsed[k]
            return parsed
        except (ValueError, SyntaxError):
            print(f"Failed to parse JSON: {cleaned[:100]}...")
            return []

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(repo_id: str):
    return os.path.join(CACHE_DIR, f"{repo_id}.json")

def save_to_cache(repo_id: str, data: dict):
    try:
        with open(get_cache_path(repo_id), "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Failed to save cache for {repo_id}: {e}")

def load_from_cache(repo_id: str):
    try:
        path = get_cache_path(repo_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load cache for {repo_id}: {e}")
    return None

async def process_analysis(repo_url: str, repo_id: str):
    print(f"Starting analysis for {repo_id}...")
    
    # Check cache first
    cached_data = load_from_cache(repo_id)
    if cached_data:
        print(f"Loaded results from cache for {repo_id}")
        results_store[repo_id] = cached_data
        return

    # Initialize partial results
    results_store[repo_id] = {
        "status": "processing",
        "bugs": None,
        "suggestions": None,
        "readme": None,
        "structure": None,
        "file_summaries": None,
        "commits": None
    }

    try:
        # Ingestion (Blocking I/O, run in thread)
        repo_id, file_tree = await asyncio.to_thread(ingestion.process_repository, repo_url)
        
        # Analysis (Parallel Execution with Progressive Updates)
        print("Starting parallel analysis...")
        
        async def run_and_update(task_func, key, *args):
            try:
                result_raw = await asyncio.to_thread(task_func, *args)
                # Parse if it's one of the JSON fields
                if key in ["bugs", "suggestions", "file_summaries"]:
                    print(f"DEBUG: {key} raw output: {result_raw[:200]}...") # Log start of output
                    result = parse_json_safely(result_raw)
                else:
                    result = result_raw
                
                # Update store incrementally
                results_store[repo_id][key] = result
                print(f"Completed {key} for {repo_id}")
            except Exception as e:
                print(f"Failed {key} for {repo_id}: {e}")
                results_store[repo_id][key] = [] if key in ["bugs", "suggestions", "file_summaries", "commits"] else f"Error: {e}"

        # Define tasks
        tasks = [
            run_and_update(analysis.analyze_bugs, "bugs", repo_id),
            run_and_update(analysis.analyze_suggestions, "suggestions", repo_id),
            run_and_update(analysis.generate_readme, "readme", repo_id),
            run_and_update(analysis.analyze_structure, "structure", repo_id, file_tree),
            run_and_update(analysis.analyze_file_summaries, "file_summaries", repo_id),
            run_and_update(ingestion.get_recent_commits, "commits", repo_url)
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Mark as completed and save to cache
        results_store[repo_id]["status"] = "completed"
        save_to_cache(repo_id, results_store[repo_id])
        
        print(f"Analysis for {repo_id} completed.")
    except Exception as e:
        print(f"Analysis failed: {e}")
        results_store[repo_id] = {
            "status": "failed",
            "error": str(e)
        }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_repo(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    repo_id = ingestion.get_repo_id(request.repo_url)
    results_store[repo_id] = {"status": "processing"}
    background_tasks.add_task(process_analysis, request.repo_url, repo_id)
    return {"message": "Analysis started", "repo_id": repo_id}

@app.get("/results/{repo_id}")
async def get_results(repo_id: str):
    result = results_store.get(repo_id)
    if not result:
        raise HTTPException(status_code=404, detail="Repo not found or analysis not started")
    return result

@app.get("/status")
def health_check():
    return {"status": "ok"}

@app.post("/api/agent/audit", response_model=AuditResponse)
async def agent_audit(request: AuditRequest):
    """Run the multi-agent self-healing pipeline.

    Loads SOUL/RULES/DUTIES from disk via agent_runtime, then executes
    Auditor → (gate) → Architect → Simulator. Returns the full transcript so
    the UI can render the validation matrix and the gitclaw tool runner can
    forward outcomes back to the agent."""
    diff_content = request.diff_content
    if not diff_content.strip():
        print(f"diff_content is empty. Dynamically fetching {request.file_path} from {request.repo_url}...")
        try:
            diff_content = await asyncio.to_thread(
                git_utils.fetch_file_content,
                request.repo_url,
                request.file_path,
                request.branch,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch file from repository: {e}")

    try:
        result = await asyncio.to_thread(
            agents.run_self_heal,
            request.repo_url,
            request.branch,
            request.file_path,
            diff_content,
        )
    except PermissionError as e:
        # Conflict matrix violation — surface as 403 so the agent can recover.
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")
    return asdict(result)


@app.post("/push")
async def push_changes(request: PushRequest):
    print(f"Received push request for {request.file_path} in {request.repo_url}")
    success, message = await asyncio.to_thread(
        git_utils.push_file,
        request.repo_url,
        request.file_path,
        request.content,
        request.commit_message,
        request.branch
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"status": "success", "message": message}


