# カスタマイズガイド

このドキュメントでは、LLM RSS Curatorをあなたのニーズに合わせてカスタマイズする方法を詳しく説明します。

## 📝 プロンプトのカスタマイズ

LLMへの指示を変更する際は、**テキストファイルを編集するだけ**（コード変更・再ビルド不要）

### 1. 評価基準の変更

```bash
vim llm-judge/prompts/user.txt
```

**例: セキュリティ記事を高く評価するように変更**

```diff
【評価基準】
- 高スコア（8-10）: 技術的な深い洞察、新しい手法・ツール紹介、実践的なチュートリアル
+ 高スコア（8-10）: セキュリティに関する深い洞察、脆弱性対策、実践的なチュートリアル
```

### 2. LLMのキャラクター変更

```bash
vim llm-judge/prompts/system.txt
```

**例: 厳格な評価者に変更**

```diff
- あなたは技術記事の価値を判定する専門家です。
+ あなたは技術記事の価値を厳格に判定するシニアエンジニアです。低品質な記事には容赦なく低スコアをつけてください。
```

### 3. 出力フィールドの追加（スキーマ駆動）

```bash
vim llm-judge/prompts/response_schema.json
```

**例: 信頼度（confidence）フィールドを追加**

```json
{
  "properties": {
    "score": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "description": "記事の価値を1-10で評価したスコア",
      "example": 8
    },
    "reason": {
      "type": "string",
      "description": "評価理由（1-2文）",
      "example": "LLMの新しいファインチューニング手法を詳細に解説..."
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "評価の信頼度",
      "example": 0.85
    }
  },
  "required": ["score", "reason", "confidence"]
}
```

**これだけで完了！**
- ✅ プロンプトに自動反映
- ✅ コードが自動的に`filter_confidence`フィールドを保存
- ✅ 例示値もスキーマから自動生成

### プロンプトバージョン管理の実践

**実験用・本番用を切り替える**

```bash
# プロンプトセットを切り替え
cp prompts-experimental/* llm-judge/prompts/

# Gitでバージョン管理
git add llm-judge/prompts/
git commit -m "Update: より厳格な評価基準に変更"
```

## 🎯 フィルタリング設定のカスタマイズ

### ユーザー設定ファイルの編集

`llm-judge/config/user_preferences.json`

```json
{
  "score_threshold": 6.0,
  "interests": [
    {
      "topic": "AI/LLMの最新情報、解説、考察記事",
      "priority": 1,
      "note": "特に技術的深掘りと根拠が明確な考察を重視"
    },
    {
      "topic": "AWS（AI/機械学習サービス、サーバレス）",
      "priority": 2
    }
  ]
}
```

### カスタマイズパターン例

#### パターンA: AI研究者向け（厳格な学術記事のみ）

```json
{
  "score_threshold": 8.0,
  "interests": ["機械学習", "深層学習", "論文"],
  "evaluation_criteria": {
    "high_score": {
      "description": "査読付き論文や実験結果を重視"
    }
  }
}
```

#### パターンB: エンジニア向け（実践的な記事）

```json
{
  "score_threshold": 6.0,
  "interests": ["チュートリアル", "ベストプラクティス", "実装例"],
  "evaluation_criteria": {
    "high_score": {
      "description": "コード例や実践的な手法を重視"
    }
  }
}
```

#### パターンC: 経営層向け（ビジネス影響）

```json
{
  "score_threshold": 7.0,
  "interests": ["市場動向", "ビジネス活用", "ROI"],
  "evaluation_criteria": {
    "high_score": {
      "description": "ビジネス価値や市場インパクトを重視"
    }
  }
}
```

## 🔄 環境変数のカスタマイズ

### .envファイルの設定

```bash
# LLMモデルの選択
FILTER_MODEL=gpt-4o-mini      # フィルター用（コスト重視）
ARTICLE_MODEL=gpt-4o          # 記事処理用（品質重視）

# 取得設定
MAX_ARTICLES_PER_FEED=10      # フィード毎の取得件数
MAX_ARTICLE_AGE_DAYS=3        # 3日以上前の記事は取得しない

# データ保持期間
RETENTION_DAYS=7              # 7日以上前の記事を削除対象に

# スクレイピング設定
TIMEOUT_SECONDS=30            # タイムアウト時間
```

### 環境別設定の例

**開発環境 (.env.dev)**

```bash
FILTER_MODEL=gpt-4o-mini
ARTICLE_MODEL=gpt-4o-mini     # コスト削減
MAX_ARTICLES_PER_FEED=3       # テスト用に少なく
RETENTION_DAYS=3              # すぐ削除
```

**本番環境 (.env.prod)**

```bash
FILTER_MODEL=gpt-4o-mini
ARTICLE_MODEL=o1-preview      # 最高品質
MAX_ARTICLES_PER_FEED=20      # 多めに取得
RETENTION_DAYS=30             # 長期保存
```

## 📚 RSSフィードの管理

### feeds.jsonの編集

`rss-feeder/config/feeds.json`

```json
{
  "feeds": [
    {
      "name": "aws",
      "url": "https://aws.amazon.com/jp/blogs/aws/feed/",
      "enabled": true
    },
    {
      "name": "my-custom-feed",
      "url": "https://example.com/feed.xml",
      "enabled": true,
      "note": "自社技術ブログ"
    },
    {
      "name": "deprecated-feed",
      "url": "https://old-blog.example.com/rss",
      "enabled": false,
      "note": "更新停止のため無効化"
    }
  ]
}
```

### フィード追加のベストプラクティス

1. **少量でテスト**: まず1-2件のフィードで動作確認
2. **enabled: false で準備**: 無効化状態で追加し、準備完了後に有効化
3. **noteフィールドを活用**: フィードの目的や注意点を記載

## 🎨 記事タイプ別プロンプトのカスタマイズ

### ニュース記事用プロンプト

`llm-processor/prompts/user_news.txt`

```plaintext
以下のニュース・速報記事を**簡潔に**要約してください。

【要約の方針】
- 重要なポイントを3-5つの箇条書きで抽出
- 事実を正確に、シンプルに伝える
- 読者が要点を素早く把握できることを最優先

[カスタマイズ例: ビジネス視点を追加]
+ ビジネスへの影響を1文で記載
```

### チュートリアル記事用プロンプト

`llm-processor/prompts/user_tutorial.txt`

```plaintext
以下の技術解説・チュートリアル記事を**じっくり詳細に**解説してください。

【解説の方針】
- 記事の技術的背景を丁寧に説明
- 重要な概念や実装の詳細を噛み砕いて解説
- 実践的な示唆やベストプラクティスを抽出

[カスタマイズ例: コード例の詳細化を追加]
+ コード例がある場合、その意図と仕組みを詳しく解説
```

## 🔧 個別コンポーネントのテスト

### 各コンポーネントを単独で実行

```bash
# RSS Feederのみ実行
docker-compose run --rm rss-feeder

# LLM Judgeのみ実行（フィルタリングテスト）
docker-compose run --rm llm-judge

# Web Scraperのみ実行
docker-compose run --rm web-scraper

# Article Processorのみ実行
docker-compose run --rm llm-processor
```

### テストデータでの動作確認

```bash
# 1. サンプルフィードで少量テスト
# feeds.jsonで MAX_ARTICLES_PER_FEED=3 に設定

# 2. 1記事だけ処理して結果を確認
docker-compose run --rm rss-feeder
# storage/rss-feeds/ を確認

docker-compose run --rm llm-judge
# filter_score が追加されているか確認

docker-compose run --rm web-scraper
# storage/scraped-articles/ を確認

docker-compose run --rm llm-processor
# storage/processed-articles/ を確認
```

## 💾 バックアップとリセット

### 状態のバックアップ

```bash
# 記事状態のバックアップ
cp shared/storage/article_states.json shared/storage/article_states.backup.json

# 設定のバックアップ
tar -czf config-backup.tar.gz \
  llm-judge/config/ \
  llm-judge/prompts/ \
  llm-processor/prompts/ \
  rss-feeder/config/
```

### リセット

```bash
# 記事状態をリセット
rm shared/storage/article_states.json

# すべての記事を削除
rm -rf shared/storage/rss-feeds/*
rm -rf shared/storage/scraped-articles/*
rm -rf shared/storage/processed-articles/*
```

## 📊 パフォーマンスチューニング

### APIコスト削減

```bash
# .env で調整
MAX_ARTICLES_PER_FEED=5       # 取得件数を制限
MAX_ARTICLE_AGE_DAYS=1        # 新しい記事のみ
RETENTION_DAYS=3              # 早めに削除
```

### 処理速度向上

```bash
# 並列処理（将来対応予定）
# PARALLEL_WORKERS=4

# タイムアウト短縮（ただし失敗が増える可能性）
TIMEOUT_SECONDS=15
```

## 🎯 ユースケース別設定例

### 毎日のニュースキャッチアップ

```json
{
  "score_threshold": 5.0,
  "interests": ["最新ニュース", "速報"],
  "max_articles_per_feed": 20,
  "retention_days": 3
}
```

### 週末の技術学習

```json
{
  "score_threshold": 7.0,
  "interests": ["チュートリアル", "詳細解説"],
  "max_articles_per_feed": 10,
  "retention_days": 14
}
```

### 特定技術の深堀り

```json
{
  "score_threshold": 8.0,
  "interests": ["RAG", "ベクトルデータベース", "LangChain"],
  "feeds": [
    {"name": "langchain-blog", "url": "..."},
    {"name": "pinecone-blog", "url": "..."}
  ]
}
```
