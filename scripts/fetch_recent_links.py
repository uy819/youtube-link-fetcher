"""
config/channels.yaml のチャンネルRSS(無料・無認証)を確認し、
公開から24時間以内の新着動画を state/seen_videos.json と突き合わせて
未処理分だけ抽出、GitHub Issue用のMarkdown本文を issue_body.md に書き出す。

RSSフィード自体にはライブ配信かどうかの情報が含まれないため、
候補動画ごとに yt-dlp でメタデータを取得し、通常の動画
(live_status == "not_live")だけを残す。ライブ配信中・配信予定・
配信アーカイブ(was_live)は除外する。

Obsidianやvaultへの書き込みは一切行わない。GitHub Actions単体で完結する。

前提:
  pip install feedparser pyyaml yt-dlp

実行:
  python scripts/fetch_recent_links.py
  -> 新着があれば issue_body.md を生成し、終了コード0で "has_new=true" を出力
  -> 新着がなければ issue_body.md を作らず終了
"""

import json
import os
from datetime import datetime, timedelta, timezone

import feedparser
import yaml
from yt_dlp import YoutubeDL

CONFIG_PATH = "config/channels.yaml"
STATE_DIR = "state"
SEEN_PATH = f"{STATE_DIR}/seen_videos.json"
ISSUE_BODY_PATH = "issue_body.md"
RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
HOURS_WINDOW = 24


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seen() -> set:
    if not os.path.exists(SEEN_PATH):
        return set()
    with open(SEEN_PATH, encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(seen: set) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def is_within_window(entry, hours: int) -> bool:
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        return False
    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - published <= timedelta(hours=hours)


def is_regular_video(url: str) -> bool:
    """ライブ配信・配信予定・配信アーカイブを除外し、通常動画のみ通す。"""
    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        # live_status: "is_live" | "is_upcoming" | "was_live" | "post_live" | "not_live" | None
        live_status = info.get("live_status")
        return live_status in (None, "not_live")
    except Exception as e:
        print(f"メタデータ取得失敗、除外扱いにします: {url} ({e})")
        return False


def main() -> None:
    config = load_config()
    seen = load_seen()
    new_entries = []

    for channel in config["channels"]:
        url = RSS_TEMPLATE.format(channel_id=channel["channel_id"])
        feed = feedparser.parse(url)

        for entry in feed.entries:
            video_id = entry.yt_videoid if hasattr(entry, "yt_videoid") else entry.id.split(":")[-1]
            if video_id in seen:
                continue
            if not is_within_window(entry, HOURS_WINDOW):
                continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            title_filter = channel.get("title_filter")
            if title_filter and title_filter not in entry.title:
                seen.add(video_id)  # 対象外は次回以降も再チェックしない
                continue

            seen.add(video_id)  # ライブ判定に関わらず既知として記録し、再チェックを避ける

            if not is_regular_video(video_url):
                print(f"ライブ系のため除外: {entry.title}")
                continue

            new_entries.append({
                "channel": channel["name"],
                "title": entry.title,
                "url": video_url,
            })

    save_seen(seen)

    github_output = os.environ.get("GITHUB_OUTPUT")

    if not new_entries:
        print("新着動画なし。")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("has_new=false\n")
        return

    lines = [f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} 時点の新着動画({HOURS_WINDOW}時間以内)", ""]
    for e in new_entries:
        lines.append(f"- [ ] [{e['title']}]({e['url']}) — {e['channel']}")

    lines.append("")
    lines.append("### コピー用URLリスト")
    lines.append("```text")
    for e in new_entries:
        lines.append(e["url"])
    lines.append("```")

    with open(ISSUE_BODY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"新着 {len(new_entries)} 件。{ISSUE_BODY_PATH} を生成しました。")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("has_new=true\n")


if __name__ == "__main__":
    main()
