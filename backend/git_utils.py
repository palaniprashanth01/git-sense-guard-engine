import os
import shutil
import tempfile
from git import Repo, Actor

def push_file(repo_url: str, file_path: str, content: str, commit_message: str, branch_name: str = "main", author_name: str = "Git Sense", author_email: str = "gitsense@example.com"):
    """
    Clones the repo, updates/creates a file, and pushes the changes.
    """
    temp_dir = tempfile.mkdtemp()
    print(f"Cloning {repo_url} to {temp_dir} for push...")
    
    try:
        # Clone the repository
        repo = Repo.clone_from(repo_url, temp_dir)
        
        # Checkout the branch (create if not exists)
        if branch_name in repo.references:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout('-b', branch_name)

        # Pull latest changes
        try:
             repo.remotes.origin.pull(branch_name)
        except Exception as e:
             print(f"Pull failed (might be new branch): {e}")

        # Write content to file
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w") as f:
            f.write(content)
        
        # Git add
        repo.index.add([file_path])
        
        # Git commit
        if repo.is_dirty(untracked_files=True):
            author = Actor(author_name, author_email)
            repo.index.commit(commit_message, author=author, committer=author)
            
            # Git push
            origin = repo.remote(name='origin')
            print(f"Pushing changes to {branch_name}...")
            push_info = origin.push(refspec=f'{branch_name}:{branch_name}')
            
            # Check for errors in push_info
            for info in push_info:
                if info.flags & (info.ERROR | info.REJECTED):
                    return False, f"Push failed: {info.summary}"

            print("Push successful.")
            return True, "Successfully pushed to repository."
        else:
            print("No changes to commit.")
            return False, "No changes to commit."

    except Exception as e:
        print(f"Failed to push changes: {e}")
        return False, str(e)
    finally:
        shutil.rmtree(temp_dir)
