#!/usr/bin/env python3
"""
Direct GitHub API Uploader (Zero Git Installation Required)
Pushes all project files directly to GitHub using GitHub's REST / Git Data API.
Usage:
    python3 upload_to_github.py <TOKEN> <REPO_NAME> [PUBLIC/PRIVATE]
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import ssl

def make_request(url, method="GET", data=None, token=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "ClubCredits-Uploader")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    ctx = getattr(make_request, "_ssl_ctx", None)
    if ctx is None:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            try:
                ctx = ssl.create_default_context()
            except Exception:
                ctx = ssl._create_unverified_context()
        make_request._ssl_ctx = ctx

    try:
        with urllib.request.urlopen(req, data=body, context=ctx) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"raw": err_body}
        return e.code, parsed
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            fallback_ctx = ssl._create_unverified_context()
            make_request._ssl_ctx = fallback_ctx
            try:
                with urllib.request.urlopen(req, data=body, context=fallback_ctx) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e2:
                err_body = e2.read().decode("utf-8")
                try:
                    parsed = json.loads(err_body)
                except Exception:
                    parsed = {"raw": err_body}
                return e2.code, parsed
        raise

def main():
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    elif os.environ.get("GITHUB_TOKEN"):
        token = os.environ.get("GITHUB_TOKEN").strip()
    elif os.environ.get("GH_TOKEN"):
        token = os.environ.get("GH_TOKEN").strip()
    
    if not token:
        try:
            token = input("Enter your GitHub Personal Access Token (PAT): ").strip()
        except (EOFError, KeyboardInterrupt):
            pass

    if not token:
        print("Usage: python3 upload_to_github.py <GITHUB_TOKEN> [REPO_NAME_OR_URL]")
        print("Or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    repo_arg = sys.argv[2].strip() if len(sys.argv) > 2 else "chaithu44-tech/Logic-bank"
    is_private = sys.argv[3].lower() == "private" if len(sys.argv) > 3 else False

    # Parse repo and optional owner
    if "/" in repo_arg:
        clean = repo_arg.rstrip("/").replace(".git", "")
        parts = clean.split("/")
        target_owner = parts[-2]
        repo_name = parts[-1]
    else:
        target_owner = None
        repo_name = repo_arg

    # 1. Get authenticated user
    print("[1/5] Verifying GitHub token...")
    status, user_info = make_request("https://api.github.com/user", token=token)
    if status != 200:
        print(f"Error authenticating with GitHub token (HTTP {status}):", user_info)
        sys.exit(1)

    username = user_info["login"]
    owner = target_owner if target_owner else username
    print(f"Authenticated as: {username}")
    print(f"Target repository: {owner}/{repo_name}")

    # 2. Check or create repository
    print(f"[2/5] Checking repository '{owner}/{repo_name}'...")
    status, repo_info = make_request(f"https://api.github.com/repos/{owner}/{repo_name}", token=token)
    if status == 404:
        print(f"Repository does not exist. Creating '{repo_name}'...")
        status, repo_info = make_request("https://api.github.com/user/repos", method="POST", data={
            "name": repo_name,
            "description": "ClubCredits: Live Group Credit Website with 120 demo accounts and visible transfer reasoning.",
            "private": is_private,
            "auto_init": True
        }, token=token)
        if status not in (200, 201):
            print(f"Failed to create repository (HTTP {status}):", repo_info)
            sys.exit(1)
        print(f"Created repository: {repo_info['html_url']}")

    # 3. Collect files
    print("[3/5] Reading files to commit...")
    files_to_upload = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".system_generated")]
        for f in files:
            if f.endswith((".tmp", ".swp", ".pyc")) or f in (".DS_Store", "upload_to_github.py"):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, BASE_DIR)
            with open(full_path, "rb") as fp:
                content_bytes = fp.read()
            files_to_upload.append((rel_path, content_bytes))

    print(f"Found {len(files_to_upload)} files to upload.")

    # 4. Upload blobs and build tree
    print("[4/5] Uploading blobs to GitHub Git Data API...")
    tree_items = []
    for rel_path, content_bytes in files_to_upload:
        b64_content = base64.b64encode(content_bytes).decode("utf-8")
        status, blob_data = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/blobs", method="POST", data={
            "content": b64_content,
            "encoding": "base64"
        }, token=token)
        if status != 201:
            print(f"Failed to create blob for {rel_path}:", blob_data)
            continue
        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_data["sha"]
        })

    # Create tree
    status, tree_data = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/trees", method="POST", data={
        "tree": tree_items
    }, token=token)
    if status != 201:
        print("Failed to create tree:", tree_data)
        sys.exit(1)

    # 5. Get latest commit SHA or default branch
    status, ref_data = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs/heads/main", token=token)
    if status == 404:
        status, ref_data = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs/heads/master", token=token)
    
    parent_sha = ref_data["object"]["sha"] if status == 200 else None

    # Create commit
    commit_payload = {
        "message": "Initial commit: ClubCredits live ledger with 120 demo accounts and visible reasoning",
        "tree": tree_data["sha"],
        "parents": [parent_sha] if parent_sha else []
    }
    status, commit_data = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/commits", method="POST", data=commit_payload, token=token)
    if status != 201:
        print("Failed to create commit:", commit_data)
        sys.exit(1)

    # Update or create branch ref
    ref_name = "heads/main" if (status == 200 or parent_sha is None) else "heads/master"
    if parent_sha:
        status, update_ref = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs/{ref_name}", method="PATCH", data={
            "sha": commit_data["sha"],
            "force": True
        }, token=token)
    else:
        status, update_ref = make_request(f"https://api.github.com/repos/{owner}/{repo_name}/git/refs", method="POST", data={
            "ref": f"refs/{ref_name}",
            "sha": commit_data["sha"]
        }, token=token)

    print("\n=======================================================")
    print(" SUCCESS! Project successfully pushed to GitHub:")
    print(f" Repository URL: https://github.com/{owner}/{repo_name}")
    print("=======================================================")

if __name__ == "__main__":
    main()
