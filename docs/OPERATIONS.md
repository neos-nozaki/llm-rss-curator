# 運用ガイド

## 📅 日次運用

### 基本的な日次ワークフロー

```bash
# 1. 新規記事の取得とフィルタリング
docker-compose run --rm rss-feeder
docker-compose run --rm llm-judge

# 2. 高評価記事のスクレイピングと要約生成
docker-compose run --rm web-scraper
docker-compose run --rm llm-processor

# 3. 記事を読む
docker-compose run --rm article-viewer --today --unread
```

### ワンライナーで全処理

```bash
# すべてのコンポーネントを順次実行
docker-compose run --rm rss-feeder && \
docker-compose run --rm llm-judge && \
docker-compose run --rm web-scraper && \
docker-compose run --rm llm-processor && \
docker-compose run --rm article-viewer --today --unread
```

## ⏰ 自動化（cron設定）

### crontabの設定例

```bash
# crontabを編集
crontab -e

# 毎朝8時に自動実行
0 8 * * * cd /path/to/llm-rss-curator && ./scripts/daily-update.sh >> /var/log/rss-curator.log 2>&1

# 毎週日曜日の深夜2時にクリーンアップ
0 2 * * 0 cd /path/to/llm-rss-curator && docker-compose run --rm data-cleanup python main.py >> /var/log/rss-cleanup.log 2>&1
```

### 自動実行スクリプト

`scripts/daily-update.sh`

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "[$(date)] Starting RSS Curator update..."

# 1. RSS取得
echo "[$(date)] Fetching RSS feeds..."
docker-compose run --rm rss-feeder

# 2. LLMフィルタリング
echo "[$(date)] Filtering with LLM..."
docker-compose run --rm llm-judge

# 3. スクレイピング
echo "[$(date)] Scraping articles..."
docker-compose run --rm web-scraper

# 4. 要約生成
echo "[$(date)] Processing articles..."
docker-compose run --rm llm-processor

echo "[$(date)] Update complete!"

# 統計を出力
docker-compose run --rm article-viewer --stats
```

実行権限を付与:

```bash
chmod +x scripts/daily-update.sh
```

## 🗄️ データ管理

### ストレージ使用量の確認

```bash
# 各ディレクトリのサイズを確認
du -sh shared/storage/rss-feeds/
du -sh shared/storage/scraped-articles/
du -sh shared/storage/processed-articles/

# 総使用量
du -sh shared/storage/
```

### データクリーンアップ

```bash
# dry-runモードで確認（削除はされない）
docker-compose run --rm data-cleanup

# 実際に削除
docker-compose run --rm data-cleanup python main.py

# 特定の保持期間で実行
docker-compose run --rm -e RETENTION_DAYS=14 data-cleanup python main.py
```

### 手動でのデータ削除

```bash
# 特定フィードの記事を削除
rm -rf shared/storage/*/aws/

# 特定期間より古い記事を削除（例: 30日以上前）
find shared/storage/rss-feeds/ -name "*.json" -mtime +30 -delete
find shared/storage/scraped-articles/ -name "*.md" -mtime +30 -delete
find shared/storage/processed-articles/ -name "*.md" -mtime +30 -delete
```

## 📊 監視とログ

### ログの確認

```bash
# 最新のログを表示
docker-compose logs rss-feeder
docker-compose logs llm-judge
docker-compose logs web-scraper
docker-compose logs llm-processor

# リアルタイムでログを監視
docker-compose logs -f rss-feeder
```

### 統計情報の取得

```bash
# 記事の統計
docker-compose run --rm article-viewer --stats

# 各フィードの記事数
find shared/storage/processed-articles/ -type f -name "*.md" | \
  sed 's|.*/\([^/]*\)/[^/]*\.md|\1|' | \
  sort | uniq -c
```

### エラーチェック

```bash
# フィルタリングされなかった記事をチェック
find shared/storage/rss-feeds/ -name "*.json" -exec grep -L "filter_score" {} \;

# スクレイピング失敗した記事をチェック
# (メタデータはあるが本文がない)
comm -23 \
  <(find shared/storage/rss-feeds/aws/ -name "*.json" | sed 's/.*\///;s/\.json//' | sort) \
  <(find shared/storage/scraped-articles/aws/ -name "*.md" | sed 's/.*\///;s/\.md//' | sort)
```

## 🔄 バックアップとリストア

### 定期バックアップ

```bash
# バックアップスクリプト
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d)

# ストレージをバックアップ
tar -czf "$BACKUP_DIR/storage-$DATE.tar.gz" shared/storage/

# 設定をバックアップ
tar -czf "$BACKUP_DIR/config-$DATE.tar.gz" \
  llm-judge/config/ \
  llm-judge/prompts/ \
  llm-processor/prompts/ \
  rss-feeder/config/ \
  .env

# 古いバックアップを削除（30日以上前）
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

### リストア

```bash
# ストレージをリストア
tar -xzf storage-20251113.tar.gz -C ./

# 設定をリストア
tar -xzf config-20251113.tar.gz -C ./
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. 記事が取得されない

```bash
# RSSフィードのURLが正しいか確認
cat rss-feeder/config/feeds.json

# 手動でフィードを確認
curl -L "https://aws.amazon.com/jp/blogs/aws/feed/" | head -20

# ログを確認
docker-compose logs rss-feeder
```

#### 2. フィルタリングスコアが全て低い

```bash
# ユーザー設定を確認
cat llm-judge/config/user_preferences.json

# プロンプトを確認
cat llm-judge/prompts/user.txt

# score_thresholdを一時的に下げてテスト
# user_preferences.json で score_threshold: 3.0 に変更
```

#### 3. スクレイピングが失敗する

```bash
# タイムアウトを延長
# .env で TIMEOUT_SECONDS=60 に変更

# 特定のサイトが403を返す場合
# USER_AGENTを変更してテスト

# ログで失敗した記事を確認
docker-compose logs web-scraper | grep "Failed"
```

#### 4. APIコストが高い

```bash
# フィルタリングを厳しくする
# score_threshold を 7.0 に上げる

# 取得記事数を制限
# MAX_ARTICLES_PER_FEED=5 に減らす

# 古い記事を取得しない
# MAX_ARTICLE_AGE_DAYS=1 に短縮
```

#### 5. ディスク容量が不足

```bash
# ストレージ使用量を確認
du -sh shared/storage/

# クリーンアップを実行
docker-compose run --rm data-cleanup python main.py

# 保持期間を短縮
# RETENTION_DAYS=3 に設定
```

## 📈 パフォーマンス最適化

### 処理速度の改善

```bash
# 並列処理数を増やす（将来対応予定）
# Docker Composeで複数コンテナを起動

# 不要なログを無効化
# LOG_LEVEL=WARNING に変更
```

### コスト最適化

```bash
# モデルの選択
FILTER_MODEL=gpt-4o-mini      # 安価なモデル
ARTICLE_MODEL=gpt-4o-mini     # テストは安価なモデル

# トークン数を制限
# user_news.txt で max_tokens=500 に削減
# user_tutorial.txt で max_tokens=1500 に削減
```

## 🔐 セキュリティ

### APIキーの管理

```bash
# .envファイルのパーミッション設定
chmod 600 .env

# Gitで追跡されないように確認
cat .gitignore | grep "^\.env$"

# 環境変数の確認（キーは表示されない）
docker-compose config | grep OPENAI_API_KEY
```

### データの暗号化

```bash
# バックアップを暗号化
tar -czf - shared/storage/ | gpg -c > storage-encrypted.tar.gz.gpg

# 復号化
gpg -d storage-encrypted.tar.gz.gpg | tar -xzf -
```

## 📱 通知の設定

### Slack通知（例）

`scripts/notify-slack.sh`

```bash
#!/bin/bash
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
STATS=$(docker-compose run --rm article-viewer --stats 2>&1)

curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"📰 RSS Curator Daily Report\n\`\`\`\n$STATS\n\`\`\`\"}" \
  "$WEBHOOK_URL"
```

cron設定:

```bash
# 毎朝9時に統計をSlackに通知
0 9 * * * /path/to/llm-rss-curator/scripts/notify-slack.sh
```

## 📚 その他のヒント

### 効率的な記事管理

```bash
# 未読記事のみを表示
docker-compose run --rm article-viewer --unread

# 高評価記事のみを表示
docker-compose run --rm article-viewer --min-score 8

# 特定フィードの未読記事
docker-compose run --rm article-viewer --feed aws --unread

# お気に入り記事の復習
docker-compose run --rm article-viewer --favorites
```

### プロンプトのA/Bテスト

```bash
# バージョンAのプロンプトで実行
cp prompts-version-a/* llm-judge/prompts/
docker-compose run --rm llm-judge
mv shared/storage/rss-feeds shared/storage/rss-feeds-version-a

# バージョンBのプロンプトで実行
cp prompts-version-b/* llm-judge/prompts/
docker-compose run --rm llm-judge
mv shared/storage/rss-feeds shared/storage/rss-feeds-version-b

# 結果を比較
diff -r shared/storage/rss-feeds-version-a shared/storage/rss-feeds-version-b
```
