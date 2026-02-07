#!/usr/bin/env python3
"""Create a Git branch/commit for a patch and optionally open a GitHub PR.

Workflow:
  - Creates branch 'patch-{id}'
  - Writes patch JSON to 'patches/pending/{id}.json'
  - Commits and pushes branch
  - If GITHUB_TOKEN and REPO env (owner/repo) are set, attempts to create a draft PR

This script is conservative and prints the commands it ran; no force-pushes.
"""

import os
import sys
import json
import subprocess
import argparse
import requests


def run(cmd):
    print('>',' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--patch-file', required=True)
    p.add_argument('--repo-root', default='.')
    p.add_argument('--push', action='store_true')
    args = p.parse_args()

    with open(args.patch_file, 'r', encoding='utf-8') as fh:
        patch = json.load(fh)
    pid = patch.get('id') or 'patch'
    branch = f'patch-{pid}'
    # Use telemetry helper to save file locally into patches/pending
    try:
        from sonarsniffer.telemetry import save_patch_locally
        out_path = save_patch_locally(patch, repo_root=args.repo_root)
    except Exception:
        target_dir = os.path.join(args.repo_root, 'patches', 'pending')
        os.makedirs(target_dir, exist_ok=True)
        out_path = os.path.join(target_dir, f'{pid}.json')
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(patch, fh, indent=2)

    try:
        # Detect default branch (origin/HEAD) or fall back to main/master
        default_branch = 'main'
        try:
            out = subprocess.check_output(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            if out and out.startswith('refs/remotes/origin/'):
                default_branch = out.split('/')[-1]
        except Exception:
            # fallback: try to detect 'main' vs 'master'
            for b in ('main', 'master'):
                try:
                    subprocess.check_call(['git', 'rev-parse', '--verify', b], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    default_branch = b
                    break
                except Exception:
                    continue

        # If branch exists, checkout it; otherwise create it
        branch_exists = False
        try:
            subprocess.check_call(['git', 'rev-parse', '--verify', branch], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            branch_exists = True
        except Exception:
            branch_exists = False

        if branch_exists:
            run(['git', 'checkout', branch])
            print(f'Using existing branch {branch}')
        else:
            run(['git', 'checkout', '-b', branch])
            print(f'Created branch {branch}')

        run(['git', 'add', out_path])
        # Only commit if there are staged changes
        try:
            run(['git', 'diff', '--cached', '--quiet'])
            print('No staged changes to commit')
        except subprocess.CalledProcessError:
            run(['git', 'commit', '-m', f'Add patch {pid}'])
            print('Committed patch file')

        if args.push:
            run(['git', 'push', '-u', 'origin', branch])
            token = os.environ.get('GITHUB_TOKEN')
            repo = os.environ.get('GITHUB_REPO')
            # Attempt to autodetect repo from git remotes if not provided
            if not repo:
                try:
                    remote = subprocess.check_output(['git', 'remote', 'get-url', 'origin']).decode('utf-8').strip()
                    # handle git@github.com:owner/repo.git and https://github.com/owner/repo.git
                    if remote.startswith('git@'):
                        repo = remote.split(':', 1)[1].rstrip('.git')
                    else:
                        repo = remote.split('github.com/')[-1].rstrip('.git')
                except Exception:
                    repo = None
            if token and repo:
                # Create draft PR
                url = f'https://api.github.com/repos/{repo}/pulls'
                headers = {'Authorization': f'token {token}'}
                data = {
                    'title': f'Patch {pid}',
                    'head': branch,
                    'base': default_branch,
                    'body': f'Automated patch {pid} submitted via script',
                    'draft': True,
                }
                try:
                    r = requests.post(url, json=data, headers=headers)
                    r.raise_for_status()
                    print('PR created:', r.json().get('html_url'))
                except Exception as ex:
                    print('PR creation failed:', ex)
    except subprocess.CalledProcessError as e:
        print('Git operation failed:', e)
        sys.exit(2)

if __name__ == '__main__':
    main()
