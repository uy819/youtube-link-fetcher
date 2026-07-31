"""
YouTube動画の字幕を取得し、Claude APIで要約する。
ANTHROPIC_API_KEY が未設定、または字幕が取得できない場合は None を返す
(呼び出し側は summary なしでフォールバックする)。

前提:
  pip install youtube-transcript-api requests
"""

import os

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"  # 日次の要約用途なのでコスト優先でHaiku
MAX_TRANSCRIPT_CHARS = 12000  # 字幕が長い場合のトークン節約用の上限


def get_transcript_text(video_id: str) -> str | None:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ja", "en"])
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"字幕取得失敗 ({video_id}): {e}")
        return None
    return " ".join(t["text"] for t in transcript)


def summarize_transcript(text: str, title: str) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None

    prompt = (
        f"以下は経済ニュース動画「{title}」の字幕全文です。\n"
        "投資家の視点で重要なポイントだけを3行以内の箇条書き(各行「- 」始まり)で"
        "日本語要約してください。前置きや結論の一言まとめは不要、箇条書きのみ出力してください。\n\n"
        + text[:MAX_TRANSCRIPT_CHARS]
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(
            block["text"] for block in data["content"] if block["type"] == "text"
        ).strip()
    except Exception as e:
        print(f"要約失敗 ({title}): {e}")
        return None


def summarize_video(video_id: str, title: str) -> str | None:
    """字幕取得→要約までをまとめて行う。失敗時はNone。"""
    transcript_text = get_transcript_text(video_id)
    if not transcript_text:
        return None
    return summarize_transcript(transcript_text, title)
