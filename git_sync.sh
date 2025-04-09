#!/bin/bash

# Script to sync all git repositories in a directory and subdirectories
# with all their remotes on a daily basis

# Usage: ./git_sync.sh /path/to/your/projects/root

# Check if directory path is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 /path/to/your/projects/root"
    exit 1
fi

ROOT_DIR="$1"
LOG_FILE="$HOME/git_sync_$(date +%Y%m%d).log"

# Ensure ROOT_DIR exists
if [ ! -d "$ROOT_DIR" ]; then
    echo "Error: Directory $ROOT_DIR does not exist" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Starting git repository sync at $(date)" | tee -a "$LOG_FILE"
echo "Scanning for git repositories in $ROOT_DIR" | tee -a "$LOG_FILE"

# Find all git repositories
find "$ROOT_DIR" -type d -name ".git" | while read -r git_dir; do
    repo_dir="${git_dir%.git}"
    
    echo "Processing repository: $repo_dir" | tee -a "$LOG_FILE"
    
    # Change to the repository directory
    cd "$repo_dir" || continue
    
    # Check if this is actually a git repository
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        echo "  Not a valid git repository, skipping..." | tee -a "$LOG_FILE"
        continue
    fi
    
    # Fetch all remotes and their branches
    echo "  Fetching from all remotes..." | tee -a "$LOG_FILE"
    git fetch --all --prune
    
    # Get current branch
    current_branch=$(git symbolic-ref --short HEAD 2>/dev/null)
    if [ -z "$current_branch" ]; then
        echo "  Not on any branch (detached HEAD), skipping push..." | tee -a "$LOG_FILE"
        continue
    fi
    
    # Get all remotes
    remotes=$(git remote)
    if [ -z "$remotes" ]; then
        echo "  No remotes configured for this repository, skipping..." | tee -a "$LOG_FILE"
        continue
    fi
    
    # For each remote, push all local branches that track remote branches
    for remote in $remotes; do
        echo "  Syncing with remote: $remote" | tee -a "$LOG_FILE"
        
        # Get all branches
        branches=$(git branch -a | grep -v HEAD | grep -v "remotes" | sed -e 's/\s*//g')
        
        # Push each branch to the remote
        for branch in $branches; do
            echo "    Pushing branch $branch to $remote" | tee -a "$LOG_FILE"
            git push "$remote" "$branch" | tee -a "$LOG_FILE" || echo "    Failed to push $branch to $remote" | tee -a "$LOG_FILE"
        done
        
        # Pull from the remote for the current branch
        echo "    Pulling updates from $remote for current branch: $current_branch" | tee -a "$LOG_FILE"
        git pull "$remote" "$current_branch" | tee -a "$LOG_FILE" || echo "    Failed to pull from $remote/$current_branch" | tee -a "$LOG_FILE"
    done
    
    echo "  Repository sync completed: $repo_dir" | tee -a "$LOG_FILE"
done

echo "All git repositories sync completed at $(date)" | tee -a "$LOG_FILE"

# To set up as a cron job at 3am daily, run:
# crontab -e
# And add this line:
# 0 3 * * * /path/to/git_sync.sh /path/to/your/projects/root 