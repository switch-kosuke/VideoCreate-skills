#!/usr/bin/env python3
"""タスク完了時に対応する GitHub Issue を自動クローズするスクリプト。

使い方:
    python scripts/close_issue.py <issue_number> [comment]

例:
    python scripts/close_issue.py 3
    python scripts/close_issue.py 3 "TopicSelector 実装完了"
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_token() -> str:
    """~/.claude/settings.json から GitHub トークンを読み込む"""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {settings_path}")
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    try:
        return settings["mcpServers"]["github"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"]
    except KeyError:
        raise KeyError("GITHUB_PERSONAL_ACCESS_TOKEN が設定ファイルに見つかりません")


def get_repo(project_root: Path) -> str:
    """git remote から owner/repo を取得する"""
    import subprocess
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    url = result.stdout.strip()
    # https://github.com/owner/repo.git または git@github.com:owner/repo.git
    if "github.com" in url:
        url = url.replace("git@github.com:", "https://github.com/")
        url = url.removesuffix(".git")
        parts = url.rstrip("/").split("/")
        return f"{parts[-2]}/{parts[-1]}"
    raise ValueError(f"GitHub リモートが見つかりません: {url}")


def close_issue(repo: str, token: str, issue_number: int, comment: str = "") -> dict:
    """GitHub Issue をクローズし、コメントを投稿する"""
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v3+json",
    }

    # コメントがあれば先に投稿
    if comment:
        comment_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
        comment_data = json.dumps({"body": comment}).encode()
        req = urllib.request.Request(comment_url, data=comment_data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                pass
        except urllib.error.HTTPError as e:
            print(f"警告: コメント投稿に失敗しました: {e}", file=sys.stderr)

    # Issue をクローズ
    patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    patch_data = json.dumps({"state": "closed", "state_reason": "completed"}).encode()
    req = urllib.request.Request(patch_url, data=patch_data, headers=headers, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> int:
    if len(sys.argv) < 2:
        print(f"使い方: {sys.argv[0]} <issue_number> [comment]", file=sys.stderr)
        return 1

    issue_number = int(sys.argv[1])
    comment = sys.argv[2] if len(sys.argv) > 2 else ""

    project_root = Path(__file__).parent.parent
    try:
        token = load_token()
        repo = get_repo(project_root)
        result = close_issue(repo, token, issue_number, comment)
        print(f"クローズしました: #{result['number']} {result['title']}")
        print(f"  URL: {result['html_url']}")
        return 0
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
