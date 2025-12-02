# トラブルシューティング

このドキュメントでは、LLM RSS Curatorで発生する可能性のある問題とその解決方法をまとめています。

## 🔧 一般的な問題

### OpenAI APIエラー

#### 症状
```
Error: OpenAI API request failed
AuthenticationError: Incorrect API key provided
```

#### 解決方法

1. **APIキーの確認**
```bash
# .envファイルを確認
cat .env | grep OPENAI_API_KEY

# APIキーが正しいか確認（OpenAIダッシュボードで確認）
```

2. **APIキーのクォータを確認**
- OpenAIダッシュボードで使用量と制限を確認
- 必要に応じてクレジットをチャージ

3. **環境変数が正しく読み込まれているか確認**
```bash
docker-compose config | grep OPENAI_API_KEY
```

### フィルタリングが厳しすぎる/緩すぎる

#### 症状
- ほとんどの記事がフィルタリングされる
- または、低品質な記事も通過してしまう

#### 解決方法

1. **スコア閾値を調整**
```bash
# llm-judge/config/user_preferences.json
{
  "score_threshold": 5.0  # 推奨: 5-7の範囲で調整
}
```

2. **興味トピックを具体化**
```json
{
  "interests": [
    "AI/LLM",  // ← 広すぎる場合は具体的に
    "RAG（Retrieval-Augmented Generation）の実装",  // ← より具体的
    "LangChainのベストプラクティス"
  ]
}
```

3. **評価基準を調整**
```bash
# llm-judge/prompts/user.txt を編集
vim llm-judge/prompts/user.txt
```

### プロンプトを変更したが反映されない

#### 症状
プロンプトファイルを編集したが、LLMの挙動が変わらない

#### 解決方法

1. **Dockerイメージを再ビルド**
```bash
docker-compose build llm-judge
```

2. **ボリュームマウントを確認**
```bash
# docker-compose.ymlでボリュームマウントされているか確認
cat docker-compose.yml | grep -A 5 "llm-judge:"
```

3. **キャッシュをクリア**
```bash
docker-compose down
docker-compose up --build
```

### 記事が重複して取得される

#### 症状
- 同じ記事が複数回処理される
- LLM Judgeが同じ記事を何度も評価している
- ログに同じ記事タイトルが繰り返し出力される

#### 原因分析（2025年11月修正済み）

**旧実装の問題:**
1. RSS Feederが既存記事を誤って再保存
2. 件数制限による削除がRSSフィードに含まれる記事を削除
3. 次回実行時、削除された記事が「新規」として再保存
4. LLM Judgeが追加した`filter_score`が消失
5. 無限ループが発生

#### 解決方法（現在のバージョン）

**システムの修正内容:**

1. **URL重複チェック**
   - 記事IDはURLのMD5ハッシュで生成（同じURLは常に同じID）
   - 既存記事は自動的にスキップ

2. **既存データの保護**
   - 既存記事がある場合、`filter_score`等を保持してマージ
   - LLM処理結果が消失しない

3. **件数制限削除の廃止**
   - 日数ベース（`RETENTION_DAYS`）の削除のみ
   - RSSフィードに含まれる記事は削除されない

**動作確認:**

```bash
# 1. RSS Feederを2回実行（2回目は新規0件のはず）
docker-compose run --rm rss-feeder
docker-compose run --rm rss-feeder

# 2. LLM Judgeを2回実行（2回目は処理対象0件のはず）
docker-compose run --rm llm-judge
docker-compose run --rm llm-judge

# 3. filter_scoreが保持されているか確認
cat shared/storage/rss-feeds/zenn-llm/*.json | grep filter_score
```

**期待されるログ:**
```
# 1回目
INFO - 完了: zenn-llm - 新規記事 9件

# 2回目（同じフィード）
INFO - 完了: zenn-llm - 新規記事 0件  ← 既存記事はスキップ
```

**問題が継続する場合:**

```bash
# 旧バージョンからの移行時、データをクリア
rm -rf shared/storage/rss-feeds/*
./run-pipeline.sh
```

## 🌐 スクレイピング関連

### スクレイピングが失敗する

#### 症状
```
ERROR: Failed to scrape article: Timeout
ERROR: HTTP 403 Forbidden
```

#### 解決方法

1. **タイムアウトを延長**
```bash
# .env
TIMEOUT_SECONDS=60  # デフォルトは30秒
```

2. **User-Agentを変更**
```bash
# .env
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

3. **特定サイトのBot対策**
```bash
# Cloudflare等のBot対策がある場合は、そのフィードを無効化
# feeds.json
{
  "name": "openai-blog",
  "enabled": false,  // ← 無効化
  "note": "Cloudflare Bot対策により取得不可"
}
```

### 動的コンテンツが取得できない

#### 症状
JavaScriptで動的に生成されるコンテンツが取得できない

#### 解決方法（将来対応予定）

現在は静的HTMLのみ対応。動的コンテンツには以下が必要:

```bash
# Playwrightの導入（将来バージョンで対応予定）
# pip install playwright
# playwright install
```

## 📊 データ関連

### ディスク容量不足

#### 症状
```
ERROR: No space left on device
```

#### 解決方法

1. **使用量を確認**
```bash
du -sh shared/storage/
du -sh shared/storage/*/
```

2. **クリーンアップを実行**
```bash
# 古い記事を削除
docker-compose run --rm data-cleanup python main.py

# 保持期間を短縮
# .env
RETENTION_DAYS=3  # デフォルトは7日
```

3. **手動で削除**
```bash
# 特定フィードを削除
rm -rf shared/storage/*/aws/

# 30日以上前のファイルを削除
find shared/storage/ -name "*.md" -mtime +30 -delete
find shared/storage/ -name "*.json" -mtime +30 -delete
```

### 状態管理ファイルが壊れた

#### 症状
```
ERROR: Failed to load article states
JSONDecodeError: Expecting value
```

#### 解決方法

1. **バックアップから復元**
```bash
cp shared/storage/article_states.backup.json shared/storage/article_states.json
```

2. **ファイルを削除してリセット**
```bash
# すべての状態がリセットされます
rm shared/storage/article_states.json
```

3. **手動で修正**
```bash
# JSONフォーマットを確認
cat shared/storage/article_states.json | jq .

# エラーがあれば手動で修正
vim shared/storage/article_states.json
```

## 🚀 パフォーマンス問題

### 処理が遅い

#### 症状
記事の処理に時間がかかりすぎる

#### 解決方法

1. **記事数を制限**
```bash
# .env
MAX_ARTICLES_PER_FEED=5  # デフォルトは10
```

2. **古い記事を除外**
```bash
# .env
MAX_ARTICLE_AGE_DAYS=1  # デフォルトは3日
```

3. **ログレベルを下げる**
```bash
# .env
LOG_LEVEL=WARNING  # デフォルトはINFO
```

### APIコストが高い

#### 症状
OpenAI APIの使用料金が予想より高い

#### 解決方法

1. **フィルタリングを厳しくする**
```json
// user_preferences.json
{
  "score_threshold": 7.0  // 閾値を上げる
}
```

2. **安価なモデルを使う**
```bash
# .env
FILTER_MODEL=gpt-4o-mini
ARTICLE_MODEL=gpt-4o-mini  # 本番は gpt-4o を推奨
```

3. **トークン数を制限**
```python
# llm-processor/prompts/user_news.txt
# max_tokens を削減（コード側で調整）
```

4. **取得記事数を減らす**
```bash
# .env
MAX_ARTICLES_PER_FEED=3
MAX_ARTICLE_AGE_DAYS=1
```

## 🐳 Docker関連

### コンテナが起動しない

#### 症状
```
ERROR: Service 'llm-judge' failed to build
```

#### 解決方法

1. **ログを確認**
```bash
docker-compose logs llm-judge
```

2. **イメージを再ビルド**
```bash
docker-compose build --no-cache llm-judge
```

3. **古いイメージとコンテナを削除**
```bash
docker-compose down
docker system prune -a
docker-compose up --build
```

### ボリュームマウントが機能しない

#### 症状
ファイルを編集してもコンテナ内で反映されない

#### 解決方法

1. **マウント設定を確認**
```bash
# docker-compose.yml
volumes:
  - ./shared/storage:/app/storage  # 正しいパス
  - ./llm-judge:/app              # ソースコードもマウント
```

2. **コンテナを再起動**
```bash
docker-compose restart llm-judge
```

3. **絶対パスを使用**
```bash
# docker-compose.yml
volumes:
  - /absolute/path/to/shared/storage:/app/storage
```

## 📱 Article Viewer関連

### 記事が表示されない

#### 症状
```
表示する記事がありません
```

#### 解決方法

1. **記事が処理されているか確認**
```bash
find shared/storage/processed-articles/ -name "*.md"
```

2. **フィルタ条件を緩和**
```bash
# --min-score や --unread などのフィルタを外す
docker-compose run --rm article-viewer
```

3. **削除済み記事も表示**
```bash
docker-compose run --rm article-viewer --show-deleted
```

### 状態が保存されない

#### 症状
既読マークやお気に入りが保存されない

#### 解決方法

1. **ストレージパスを確認**
```bash
# article_states.json が作成されているか確認
ls -la shared/storage/article_states.json
```

2. **書き込み権限を確認**
```bash
# ディレクトリに書き込み権限があるか確認
ls -ld shared/storage/
chmod 755 shared/storage/
```

3. **手動で状態ファイルを作成**
```bash
echo '{"read": {}, "deleted": {}, "favorite": {}, "archived": {}}' > shared/storage/article_states.json
```

## 🔍 デバッグ方法

### ログレベルを上げる

```bash
# .env
LOG_LEVEL=DEBUG
```

### 特定コンポーネントのデバッグ

```bash
# Pythonのデバッグモードで実行
docker-compose run --rm llm-judge python -m pdb main.py
```

### ファイル出力を確認

```bash
# 各段階の出力を確認
ls -la shared/storage/rss-feeds/aws/
cat shared/storage/rss-feeds/aws/example-id.json | jq .

ls -la shared/storage/scraped-articles/aws/
head -20 shared/storage/scraped-articles/aws/example-id.md

ls -la shared/storage/processed-articles/aws/
head -20 shared/storage/processed-articles/aws/example-id.md
```

## 📞 サポート

問題が解決しない場合:

1. **GitHubでIssueを作成**
   - エラーメッセージ全文
   - 実行したコマンド
   - 環境情報（OS、Dockerバージョン）

2. **ログを添付**
```bash
docker-compose logs > debug.log
```

3. **設定ファイルを確認**
   - `.env`（APIキーは削除）
   - `feeds.json`
   - `user_preferences.json`
