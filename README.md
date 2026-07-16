# YouTube新着リンク自動通知(GitHub単体)

Obsidian・Claude・NotebookLMのどれにも依存せず、GitHub Actionsだけで
完結する。毎朝、登録チャンネルの新着動画(24時間以内)をチェックし、
新着があればこのリポジトリにGitHub Issueとして起票する。
GitHubのWeb画面でもモバイルアプリでも確認でき、チェックリスト形式
なので処理済みを都度チェックしていける。

## 仕組み

1. `scripts/fetch_recent_links.py` がチャンネルの公開RSSフィード
   (`https://www.youtube.com/feeds/videos.xml?channel_id=...`、
   認証不要・無料)を取得
2. `state/seen_videos.json` と突き合わせ、24時間以内かつ未処理の
   動画だけを抽出
3. 新着があれば `gh issue create` でIssueを起票、`state/`をコミット
4. 新着がなければ何もしない(Issueも作られない)

課金要素なし。GitHub Actionsの無料枠内で完結する。

## セットアップ手順

1. このフォルダの中身をGitHubリポジトリのルートにpush
   ```bash
   git init
   git add .
   git commit -m "Initial setup"
   git remote add origin <あなたのリポジトリURL>
   git push -u origin main
   ```
2. 特別なSecrets設定は不要(`GITHUB_TOKEN`はActionsが自動発行する)
3. `config/channels.yaml` に監視したいチャンネルを追加。
   「テレ東BIZ ダイジェスト」は登録済み(`UCkKVQ_GNjd8FbAuT6xDcWgg`)。
   他チャンネルの`channel_id`は `youtube.com/channel/UCxxxx` の
   `UCxxxx` 部分
4. リポジトリの Settings → Actions → General → Workflow permissions で
   "Read and write permissions" を有効化(Issue作成とpushに必要)
5. 初回は Actions タブから `Daily YouTube Links to Issue` を
   `workflow_dispatch` で手動実行し、Issueが作られるか確認する

## 運用

毎朝、リポジトリのIssuesタブ(またはGitHubモバイルアプリの通知)を開き、
その日の新着リンクをチェックリストで確認する。そこから先
(NotebookLMへの貼り付け、要約のObsidianへの転記)は従来通り手動で行う。
このリポジトリは「リンクを探す」工程だけを肩代わりする、完全に独立した
ツールという位置づけ。
