# LLM RSS Curator

**LLMが記事を事前評価し、価値ある記事だけを記事特性に応じて最適に処理**する次世代RSSリーダー。
記事タイプを自動判別し、タイプ別にLLMの振る舞いをプロンプトで制御。例えばニュースは簡潔要約、チュートリアルは詳細解説など。
**すべての振る舞いを外部ファイルで制御可能**、コード変更なしで自分専用の記事キュレーションエンジンを構築できます。

## 🔄 処理フローの全体像

### 4段階の自動処理パイプライン

```
1️⃣ RSS Feeder (記事メタデータ収集)
   ↓
   RSSフィードから title, summary, link, published を取得
   ↓
   storage/rss-feeds/{feed_name}/{article_id}.json に保存

2️⃣ LLM Judge (LLMによる価値判定 + タイプ分類) ★ Judge as LLM
   ↓
   メタデータを読み込み (title + summary のみ)
   ↓
   LLMに送信 (FILTER_MODEL: gpt-4o-mini)
   ↓
   LLMが判定:
   - score: 1-10 のスコア評価
   - reason: 評価理由
   - article_type: "news" or "tutorial" ★ タイプ判定
   ↓
   メタデータに追加保存:
   {
     ...元のフィールド,
     "filter_score": 8,
     "filter_reason": "技術的に詳細で実践的",
     "article_type": "tutorial"  ★ 記事タイプを保存
   }

3️⃣ Web Scraper (本文抽出) ★ スコアフィルタリング
   ↓
   filter_score >= threshold の記事のみ処理 ← ★低スコア記事はここで除外
   （スコア不足の記事は以降の処理に進まない）
   ↓
   記事URLからHTML取得 → Markdown変換
   ↓
   storage/scraped-articles/{feed_name}/{article_id}.md に保存

4️⃣ Article Processor (要約・解説生成) ★ タイプ別処理切り替え
   ↓
   スクレイピング済み記事のメタデータから article_type を読み込み
   ↓
   article_type に応じてプロンプト動的選択:
   - "news" → user_news.txt (簡潔な要約, max_tokens=800)
   - "tutorial" → user_tutorial.txt (詳細な解説, max_tokens=2000)
   ↓
   選択したプロンプトで LLM に送信 (ARTICLE_MODEL: gpt-4o)
   ↓
   storage/processed-articles/{feed_name}/{article_id}.md に保存
```

### 🎯 データの流れと重要なポイント

**Judge as LLMによる二段階フィルタリング:**
1. **判定タイミング**: LLM Judge段階（記事本文を読む前）
2. **判定者**: LLM（title + summaryから判断）
3. **判定結果**: `score` (価値) + `article_type` (タイプ)
4. **第1のフィルタリング**: Web Scraperが`score >= threshold`の記事のみ処理
5. **効果**: 低価値記事はスクレイピングも要約も実行されない（コスト削減）

**記事タイプ別処理の自動切り替え:**
- **分類**: LLMが記事の性質を判定（ニュース系 vs 解説系）
- **保存**: メタデータJSONファイル（`storage/rss-feeds/`）に記録
- **伝達**: Article Processorが同じJSONファイルを読み込み
- **活用**: 対応するプロンプトファイル（`user_{article_type}.txt`）を動的に選択
- **結果**: 同じコードで異なる処理スタイルを自動適用

**完全な疎結合設計:**
```
LLM Judge → メタデータJSON保存 (score + article_type)
               ↓
         共有ストレージ経由
               ↓
Web Scraper → メタデータJSON読込 → scoreチェック → 閾値以上のみ処理
               ↓
         本文をMarkdownで保存
               ↓
Article Processor → メタデータJSON読込 → article_type取得
               ↓
         プロンプト動的選択 → 要約/解説生成
```

## 🌟 このシステムの核心的強み

### 1. 🧠 Judge as LLM - AIによる記事選定

**人間のキュレーターをLLMで再現**。記事の価値判定を完全に自動化します。

```
従来: 全記事を処理 → 後で人間が選別
本システム: LLMが事前選別 → 価値ある記事だけ処理
```

**なぜ強力か:**
- 🎯 **文脈理解**: タイトル・要約から記事の本質を理解
- 📊 **定量評価**: 1-10のスコアで客観的に判定
- 🎨 **カスタマイズ**: あなたの基準でLLMを訓練（プロンプトで）
- 💰 **コスト最適化**: 低価値記事の処理を回避

### 2. 🔀 記事タイプ別の自動処理切り替え + プロンプト最適化

**同じ記事処理でも、ニュースは簡潔に、チュートリアルは詳細に**。LLMが記事タイプを判定し、**タイプごとに専用設計されたプロンプト**を自動選択することで、各記事に最適な処理を実現します。

**重要**: スコアが閾値（`score_threshold`）を満たさない記事は、Web Scraper段階で除外され、Article Processorには到達しません。つまり、**価値ある記事だけが、そのタイプに最適化された処理を受けます**。

**処理の違い（プロンプト最適化の例）:**

| タイプ       | プロンプト          | max_tokens | プロンプトの特徴                                     | 出力スタイル                 | 処理条件           |
|--------------|---------------------|------------|------------------------------------------------------|------------------------------|--------------------|
| **news**     | `user_news.txt`     | 800        | 「簡潔に」「重要ポイントのみ」「事実を正確に」       | 📰 重要ポイントを3-5行で要約  | score >= threshold |
| **tutorial** | `user_tutorial.txt` | 2000       | 「背景を説明」「技術詳細を解説」「実践的示唆を抽出」 | 📚 背景・詳細・示唆を含む解説 | score >= threshold |

**なぜ強力か:**

🎯 **自動切り替え**だけでなく、**各タイプに最適化されたプロンプト**を使うことで：
- 📰 **ニュース記事**: 「重要ポイントを3-5行で」という指示で、素早く事実を把握
- 📚 **チュートリアル記事**: 「背景・詳細・実践的示唆」を求める指示で、深い理解を促進
- 🚀 **処理品質の向上**: 記事特性に合わせた指示でLLMの性能を最大化
- 💰 **コスト最適化**: 必要な情報量に応じてトークン数を調整
- 🎯 **二重フィルタリング**: スコア不足の記事は処理されないため、さらにコスト削減

**判定と最適化の実例:**
- "OpenAI、GPT-4 Turbo発表" (score: 9) → `news` → 簡潔な要約を生成
- "RAGシステム構築完全ガイド" (score: 8) → `tutorial` → 詳細な解説を生成
- "広告記事" (score: 3) → 閾値未満 → **Scraperで除外、Processorには到達しない**

**技術的実現:**
1. **判定**: LLM Judge段階でLLMが`score`と`article_type`を判定（title + summaryから）
2. **保存**: メタデータ（JSON）に両方のフィールドを保存
3. **第1フィルタ**: Web Scraperが`score >= threshold`の記事のみスクレイピング
4. **読込**: Article Processorがスクレイピング済み記事のメタデータから`article_type`を読み込み
5. **最適化選択**: `user_{article_type}.txt`を動的に選択 ← **各タイプに特化したプロンプト**

### 3. 🎨 究極のカスタマイズ性

評価基準からLLMの振る舞いまで、**すべて外部ファイルで制御**。コードを一切触らずに、あなた専用の記事選別エンジンを作れます。

```bash
# 例1: セキュリティ専門家向けに最適化
vim llm-judge/prompts/user.txt
# → 「脆弱性」「エクスプロイト」を高く評価するように変更

# 例2: 初心者向けチュートリアルを優先
vim llm-judge/config/user_preferences.json
# → interests に「入門」「わかりやすい解説」を追加

# 例3: 厳格なキュレーションに変更
vim llm-judge/prompts/system.txt
# → LLMを「辛口評論家」に設定
```

**変更後、Dockerコンテナを再起動するだけ。コード変更ゼロ。**

## ✨ 主要な特徴

### 1. 選定基準の完全外部化（ノーコードカスタマイズ）

LLMがどう判断するか、何を重視するか、すべて**テキストファイルで定義**。

**カスタマイズ可能な要素:**
- 📝 **評価基準** (`llm-judge/prompts/user.txt`): 何を高く評価するか
- 🎭 **LLMの性格** (`llm-judge/prompts/system.txt`): 厳格? 寛容? あなた次第
- 🎯 **興味トピック** (`llm-judge/config/user_preferences.json`): 専門分野を指定
- 📊 **閾値** (`llm-judge/config/user_preferences.json`): どこまで厳しく選別するか
- 🏗️ **出力形式** (`llm-judge/prompts/response_schema.json`): 信頼度など追加フィールドも自由

**実例: 同じコードで3つの異なる用途**
```bash
# パターンA: AI研究者向け（厳格な学術記事のみ）
interests: ["機械学習", "深層学習", "論文"]
score_threshold: 8.0
評価基準: "査読付き論文や実験結果を重視"

# パターンB: エンジニア向け（実践的な記事）
interests: ["チュートリアル", "ベストプラクティス", "実装例"]
score_threshold: 6.0
評価基準: "コード例や実践的な手法を重視"

# パターンC: 経営層向け（ビジネス影響）
interests: ["市場動向", "ビジネス活用", "ROI"]
score_threshold: 7.0
評価基準: "ビジネス価値や市場インパクトを重視"
```

**すべて同じプログラム、設定ファイルだけ変更。**

### 2. LLMによる事前フィルタリング（二段階選別プロセス）

全記事を盲目的に処理するのではなく、まずRSSのタイトルと要約文をLLMに渡し、「要約する価値のある記事」を選別します。

**メリット:**
- 📉 **APIコスト削減**: 価値の低い記事のスクレイピング・要約を回避
- 🎯 **ノイズ除去**: 興味のない記事を自動フィルタリング
- ⚡ **処理効率化**: 本当に重要な記事だけを処理

**設定例:**
```json
// llm-judge/config/user_preferences.json（ユーザー固有の設定）
{
  "score_threshold": 6.0,
  "interests": [
    "AI/LLM",
    "クラウドアーキテクチャ",
    "DevOps",
    "セキュリティ",
    "技術的深堀り記事"
  ]
}
```

### 3. Markdown形式でのスクレイピング

記事本文を単なるプレーンテキストではなく、**Markdown形式**で抽出します。

**メリット:**
- 📝 **構造保持**: 見出し、箇条書き、引用など記事の意味的構造を保持
- 🤖 **LLM精度向上**: 構造化されたテキストでLLMがより正確に要約を生成
- 🔍 **文脈把握**: 重要なポイントを見逃さない

**技術:**
- `html2text`ライブラリでHTMLをMarkdownに変換
- 記事の階層構造やリストを維持

### 4. プロンプトの外部ファイル化（Schema-Driven Design)

LLMへの指示（プロンプト）をコードから完全に分離し、**スキーマ駆動**で管理します。

**設計哲学:**
- 🎯 **Single Source of Truth**: `response_schema.json`が唯一の仕様定義
- 🔄 **動的プロンプト生成**: スキーマを変更するだけでプロンプトが自動更新
- 📦 **3層分離アーキテクチャ**: 
  - `system.txt`: LLMの役割・キャラクター定義
  - `user.txt`: タスクの内容・評価基準
  - `response_schema.json`: 出力形式の仕様（型・制約・例示値）

**メリット:**
- 🔧 **完全疎結合**: データ（プロンプト）と手続き（プログラム）が独立
- 🚀 **差し替え容易**: テキストファイルを編集するだけ、コード変更・再ビルド不要
- 📊 **A/Bテスト**: 複数バージョンのプロンプトを試して効果を科学的に比較
- 📚 **バージョン管理**: プロンプトの変更履歴をGitで追跡可能
- 🎨 **拡張性**: フィールド追加時もスキーマに`example`を書くだけ
- 🛡️ **整合性保証**: プロンプトとバリデーションが常に一致

**ファイル構成:**
```
llm-judge/prompts/
  ├── system.txt           # LLMの役割定義（例: "あなたは専門家です"）
  ├── user.txt             # 評価基準とタスク指示
  └── response_schema.json # 出力形式の仕様（properties, required, example）
```

**具体例: フィールド追加がどれだけ簡単か**
```json
// response_schema.json に3行追加するだけ
{
  "confidence": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "description": "評価の信頼度",
    "example": 0.85
  }
}
```
→ プロンプトに自動反映 → コードが自動的に`filter_confidence`フィールドを保存 🎉

## 📐 設計哲学: ファイルの使い分け

このプロジェクトでは、設定データを**役割ごとに明確に分離**しています。

### 1️⃣ .env - 環境固有の設定

実行環境によって変わる値。**Gitで管理しない**（`.gitignore`に含める）

| 設定項目          | 役割                | 例            |
|-------------------|---------------------|---------------|
| `OPENAI_API_KEY`  | APIキー（秘密情報） | `sk-proj-...` |
| `FILTER_MODEL`    | フィルター用モデル  | `gpt-4o-mini` |
| `ARTICLE_MODEL`   | 記事処理用モデル    | `gpt-4o`      |
| `TIMEOUT_SECONDS` | タイムアウト時間    | `30`          |
| `RETENTION_DAYS`  | データ保持期間      | `7`           |

**なぜ`.env`か？**
- 🔐 秘密情報（APIキー）を含む
- 🎛️ 環境ごとに変更（開発ではmini、本番ではo1など）
- 🔄 簡単に上書き可能（`docker-compose`で自動読み込み）

### 2️⃣ *.json - 構造化された設定データ

複数項目やネストした構造を持つ設定。**Gitで管理する**

| ファイル                | 役割               | 内容                        |
|-------------------------|--------------------|-----------------------------|
| `feeds.json`            | RSSフィード一覧    | URLリスト、enabled/disabled |
| `user_preferences.json` | ユーザー固有の設定 | interests、score_threshold  |
| `response_schema.json`  | LLM出力の仕様      | 型定義、制約、例示値        |

**なぜJSONか？**
- 📋 複数要素のリスト（フィード、興味トピック、フィールド定義）
- 🏗️ 階層構造（properties, required, example）
- ✅ バリデーション（スキーマとして利用）

### 3️⃣ *.txt - 自然言語テンプレート

LLMに送るプロンプト。**Gitで管理する**

| ファイル     | 役割          | 内容                             |
|--------------|---------------|----------------------------------|
| `system.txt` | LLMの役割定義 | 「あなたは専門家です」           |
| `user.txt`   | タスク指示    | 評価基準、{変数}プレースホルダー |

**なぜテキストファイルか？**
- 📝 自然言語の文章
- 🔍 可読性（JSONエスケープ不要）
- 🎨 簡単に編集（コードエディタで直接編集）

### 🎯 設計の一貫性と責務分離

```
環境変数 (.env)               → 環境依存（APIキー、モデル名）
  ↓
ユーザー設定 (config/*.json)  → ユーザー依存（興味、フィード、閾値）
  ↓ 動的に埋め込み
テンプレート (prompts/*.txt) → 自然言語、再利用可能
  ↓ スキーマ参照
出力仕様 (prompts/*.json)    → LLM出力の型定義
```

**重要な設計原則: 環境依存 vs ユーザー依存 vs データ構造の分離**
| 設定項目           | 配置先                         | 依存性           | 理由                                   |
|--------------------|--------------------------------|------------------|----------------------------------------|
| APIキー            | `.env`                         | 環境依存         | 開発/本番で異なる秘密情報              |
| フィルター用モデル | `.env`                         | 環境依存         | 開発ではmini、本番でもminiなど         |
| 記事処理用モデル   | `.env`                         | 環境依存         | 開発ではgpt-4o、本番ではo1-previewなど |
| タイムアウト       | `.env`                         | 環境依存         | 環境のネットワーク速度によって異なる   |
| **興味トピック**   | `config/user_preferences.json` | **ユーザー依存** | **ユーザーAとBで異なる（環境不問）**   |
| **閾値**           | `config/user_preferences.json` | **ユーザー依存** | **ユーザーの厳格度の好み**             |
| フィード一覧       | `config/feeds.json`            | ユーザー依存     | ユーザー固有の購読リスト               |
| LLM出力仕様        | `prompts/response_schema.json` | データ構造       | 型定義、すべてのユーザー・環境で共通   |

**メンテナンスシナリオの例:**
```bash
# ケース1: 興味トピックを変更（ユーザー設定ファイルを編集）
vim llm-judge/config/user_preferences.json
# "interests"配列に新しいトピックを追加

# ケース2: 環境別のモデルを変更（環境変数を編集）
echo "ARTICLE_MODEL=gpt-4o" >> .env.production  # 本番は高品質モデル

# ケース3: 評価基準を変更（プロンプトファイルを編集）
vim llm-judge/prompts/user.txt

# ケース4: 出力フィールドを追加(スキーマを編集)
vim llm-judge/prompts/response_schema.json
# → コードは自動的に新フィールドを処理

# ケース5: プロンプトセットを切り替え(ファイル差し替え)
cp prompts-experimental/* llm-judge/prompts/
```

**コード変更・再ビルド不要！** 🎉

## 📚 ドキュメント

詳細なドキュメントは[docs/](docs/)ディレクトリにあります。

- **[記事閲覧ツール完全ガイド](docs/ARTICLE_VIEWER.md)** - インタラクティブモード、ページャー機能、フィルタリング、既読管理
- **[カスタマイズガイド](docs/CUSTOMIZATION.md)** - プロンプト編集、フィルタリング設定、フィード追加
- **[運用ガイド](docs/OPERATIONS.md)** - 自動化、監視、バックアップ
- **[トラブルシューティング](docs/TROUBLESHOOTING.md)** - 問題解決とデバッグ
- **[アーキテクチャ](docs/ARCHITECTURE.md)** - 設計思想と技術詳細

## クイックスタート

### 1. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、必要な値を設定:

```bash
cp .env.example .env
vim .env  # OPENAI_API_KEYなどを設定
```

### 2. RSSフィードの設定

`rss-feeder/config/feeds.json`を編集して、取得したいRSSフィードを追加:

```json
{
  "feeds": [
    {
      "name": "tech-news",
      "url": "https://news.ycombinator.com/rss",
      "enabled": true
    }
  ]
}
```

### 3. Dockerコンテナの起動

```bash
# 1. RSS Feederを実行（新規記事メタデータ取得）
docker-compose run --rm rss-feeder

# 2. LLM Judgeを実行（LLMで記事の価値を判定）
docker-compose run --rm llm-judge

# 3. Web Scraperを実行（高評価記事の本文をMarkdown形式で抽出）
docker-compose run --rm web-scraper

# 4. Article Processorを実行（要約・解説生成）
docker-compose run --rm llm-processor
```

### 4. 記事を読む

要約された記事は`shared/storage/processed-articles/`に保存され、Article Viewerで快適に閲覧できます:

```bash
# インタラクティブモードで記事を読む（ページャー機能付き）
docker-compose run --rm article-viewer

# 未読記事のみ表示
docker-compose run --rm article-viewer --unread

# 今日の記事のみ
docker-compose run --rm article-viewer --today --unread
```

詳細は[記事閲覧ツール完全ガイド](docs/ARTICLE_VIEWER.md)を参照してください。

## システムアーキテクチャ

```
llm-rss-curator/
├── docker-compose.yml              # Dockerオーケストレーション
├── .env                            # 環境変数（Git管理外）
├── rss-feeder/              # RSSフィード取得
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── config/feeds.json
├── llm-judge/              # LLM事前フィルタリング
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config/
│   │   └── user_preferences.json  # ユーザー固有の設定（興味、閾値）
│   └── prompts/                   # プロンプト外部ファイル
│       ├── system.txt             # LLMの役割定義
│       ├── user.txt               # 評価基準と指示
│       └── response_schema.json   # 出力形式のスキーマ (score, reason, article_type)
├── web-scraper/             # Webスクレイピング（Markdown出力）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── llm-processor/       # 記事処理（要約・解説生成)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── prompts/                   # プロンプト外部ファイル（記事タイプ別）
│       ├── system.txt             # LLMの役割定義
│       ├── user_news.txt          # ニュース系記事用（簡潔な要約）
│       └── user_tutorial.txt      # チュートリアル系記事用（詳細な解説）
├── data-cleanup/            # データクリーンアップ（古い記事の削除）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── shared/
    └── storage/                    # ローカルストレージ
        ├── rss-feeds/              # RSSメタデータ（JSON + filter結果）
        ├── scraped-articles/       # スクレイピング済み記事（Markdown）
        └── processed-articles/      # 要約記事（Markdown）
```

**各コンポーネントの役割:**
- **RSS Feeder**: RSSフィードから新規記事のメタデータを取得
- **LLM Judge**: LLMで記事を評価（スコア + タイプ判定）
- **Web Scraper**: 高スコア記事のみ本文をMarkdown形式で抽出
- **Article Processor**: 記事タイプ別に最適化された要約・解説を生成
- **Data Cleanup**: 古い記事データの自動削除

詳細な処理フローは冒頭の「🔄 処理フローの全体像」を参照してください。

## データクリーンアップ

### 🗑️ 古い記事の自動削除

`data-cleanup`ツールは、指定した保持期間（`RETENTION_DAYS`）を超過した記事を一括削除します。

**削除対象:**
- メタデータ（`storage/rss-feeds/`）
- スクレイピング済み本文（`storage/scraped-articles/`）
- 要約・解説（`storage/processed-articles/`）

**実行方法:**

```bash
# 1. dry-runモード（削除予定を確認、実際には削除しない）
docker-compose run --rm data-cleanup

# 2. 実削除モード
docker-compose run --rm data-cleanup python main.py

# 3. 特定の保持期間で実行（例: 7日間）
docker-compose run --rm -e RETENTION_DAYS=7 data-cleanup python main.py
```

**設定:**

`.env`ファイルで保持期間を設定:
```bash
RETENTION_DAYS=30  # 30日以上前の記事を削除
```

**安全性:**
- デフォルトは**dry-runモード**（`docker-compose.yml`のコマンド設定）
- 削除前に必ず対象記事をログ出力
- 削除統計（件数、削除ファイル数）を表示

**ログ例:**
```
INFO: Checking articles older than 2024-10-01 00:00:00
INFO: Found 15 articles to delete
INFO: [DRY RUN] Would delete: tech-news/article123
INFO: [DRY RUN] Would delete: tech-news/article456
...
INFO: Cleanup complete: 15 articles, 45 files would be deleted
```

**定期実行の設定:**

cronやシステムのスケジューラーで定期実行:
```bash
# 毎週日曜日の深夜2時に実行（cron例）
0 2 * * 0 cd /path/to/llm-rss-curator && docker-compose run --rm data-cleanup python main.py
```

## 開発

### プロンプトのカスタマイズ

LLMへの指示を変更する際は、**テキストファイルを編集するだけ**（コード変更・再ビルド不要）：

#### 1. 評価基準の変更
```bash
vim llm-judge/prompts/user.txt
```

例: 「セキュリティ記事を高く評価」に変更
```diff
【評価基準】
- 高スコア（8-10）: 技術的な深い洞察、新しい手法・ツール紹介、実践的なチュートリアル
+ 高スコア（8-10）: セキュリティに関する深い洞察、脆弱性対策、実践的なチュートリアル
```

#### 2. LLMのキャラクター変更

```bash
vim llm-judge/prompts/system.txt
```

例: 「厳格な評価者」に変更
```diff
- あなたは技術記事の価値を判定する専門家です。
+ あなたは技術記事の価値を厳格に判定するシニアエンジニアです。低品質な記事には容赦なく低スコアをつけてください。
```

#### 3. 出力フィールドの追加（スキーマ駆動）

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
- ✅ プロンプトに自動反映（「confidence: 0-1の数値 - 評価の信頼度」が追加される）
- ✅ コードが自動的に`filter_confidence`フィールドをメタデータに保存
- ✅ 例示値もスキーマから自動生成

**差し替えの簡単さを実感:**
- プロンプトファイルを丸ごと別バージョンに入れ替え可能
- 実験用・本番用を切り替えるのも`cp`コマンド1つ
- Gitでバージョン管理すれば、いつでも過去のプロンプトに戻せる

### フィルタリング設定のカスタマイズ

`llm-judge/config/user_preferences.json`でフィルタリング設定を変更:

```json
{
  "score_threshold": 6.0,
  "interests": [
    "AI/LLM",
    "クラウドアーキテクチャ",
    "DevOps"
  ]
}
```

### 個別のコンポーネントをテスト

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

## ベストプラクティス

### なぜ二段階選別プロセスなのか？

従来の一括処理方式では:
- ❌ 興味のない記事もスクレイピング・要約（コスト・時間の無駄）
- ❌ ノイズが多く、重要な記事が埋もれる
- ❌ APIコストが高騰

**二段階選別プロセスの効果:**
- ✅ APIコスト50-70%削減の可能性
- ✅ 重要な記事だけを処理
- ✅ プロンプトファイルで評価基準を簡単に調整可能

### なぜプロンプトを外部ファイル化するのか？

**従来のハードコード方式:**
- ❌ プロンプト変更のたびにコード編集・再ビルド必要
- ❌ 評価基準の履歴管理が困難
- ❌ A/Bテストが煩雑

**外部ファイル方式のメリット:**
- ✅ テキストエディタで即座に編集・反映
- ✅ Gitで変更履歴を追跡
- ✅ JSON Schemaで出力形式を柔軟に拡張
- ✅ 複数のプロンプトバージョンを比較可能

### なぜMarkdown形式なのか？

**プレーンテキスト:**
```
製品の特徴
高速処理
セキュア
スケーラブル
```
→ LLMは「ただの箇条書き」と認識、構造を失う

**Markdown:**
```markdown
## 製品の特徴
- 高速処理
- セキュア
- スケーラブル
```
→ LLMは「見出しと箇条書きの構造」を認識、要約精度が向上

## トラブルシューティング

### OpenAI APIエラー

- `.env`ファイルの`OPENAI_API_KEY`が正しく設定されているか確認
- APIキーのクォータが残っているか確認

### フィルタリングが厳しすぎる/緩すぎる

- `llm-judge/config/user_preferences.json`の`score_threshold`を調整（1-10、推奨: 5-7）
- `interests`に具体的なキーワードを追加
- `llm-judge/prompts/user.txt`で評価基準を修正

### プロンプトを変更したが反映されない

- Dockerイメージを再ビルド: `docker-compose build llm-judge`
- コンテナを再起動して確認

### 記事が重複して取得される

- `shared/storage/rss-feeds/`を確認し、既存の記事IDと照合されているか確認

### スクレイピングが失敗する

- `TIMEOUT_SECONDS`を増やす（`.env`）
- 対象サイトが動的レンダリング（JavaScript）を使用している場合、Playwrightの導入を検討

### OpenAIブログ記事が取得できない

**2025年11月より、OpenAI公式ブログはCloudflare Bot Management（チャレンジ）を導入したため、通常のHTTPリクエストでは403エラーとなります。**

- OpenAIフィードはデフォルトで無効化されています（`rss-feeder/config/feeds.json`の`enabled: false`）
- Playwright（ヘッドレスブラウザ）でも突破できませんでした（Cloudflare Bot対策が強力）
- 代替: AWS、Azure、Zennなど他の技術ブログフィードを活用してください

## ライセンス

MIT License

