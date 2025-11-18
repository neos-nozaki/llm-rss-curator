# 📖 Article Viewer - 記事閲覧ツール

**ターミナルで動作するページャ付属のpopメールクライアント風RSSビューアで、既読だけでなくお気に入りも管理できる**

処理済みの要約・解説記事を読みやすく表示するCLIツールです。
**既読・未読・お気に入り・削除管理機能**を搭載しています。

## ✨ 主な機能

- 📖 **既読・未読管理**: 記事を開くと自動で既読マーク。未読記事だけをフィルタ表示可能
- ⭐ **お気に入り管理**: 重要な記事にお気に入りマーク。お気に入りだけを一覧表示
- 🗑️ **削除管理**: 不要な記事を非表示に（ファイルは保持）。削除解除も可能
- 📊 **統計情報**: 既読数、お気に入り数などの統計を表示
- 🎨 **視覚的な表示**: Rich ライブラリで美しいターミナルUI
- 📄 **ページャー機能**: スクロール可能なページャー表示で長い記事も快適に閲覧

## 🚀 クイックスタート

### 即座に使える主要コマンド

```bash
# すべての記事を読む（インタラクティブモード）
docker-compose run --rm article-viewer

# 未読記事だけを読む
docker-compose run --rm article-viewer --unread

# 今日の未読記事だけ
docker-compose run --rm article-viewer --today --unread

# お気に入り記事を再読
docker-compose run --rm article-viewer --favorites

# 統計情報を確認
docker-compose run --rm article-viewer --stats
```

### おすすめワークフロー

**毎朝のルーティン:**
```bash
# 1. 統計確認
docker-compose run --rm article-viewer --stats

# 2. 今日の未読記事を読む
docker-compose run --rm article-viewer --today --unread
```

**週末のキャッチアップ:**
```bash
# 今週の高評価記事を読む
docker-compose run --rm article-viewer --week --min-score 7 --unread
```

**フィルタリング例:**
```bash
# 高評価記事のみ（スコア8以上）
docker-compose run --rm article-viewer --min-score 8 --unread

# AWS記事のみ
docker-compose run --rm article-viewer --feed aws --unread

# チュートリアル記事のみ
docker-compose run --rm article-viewer --type tutorial --unread
```

## 📋 全オプション一覧

### フィルタオプション

| オプション            | 説明                 | 例                |
|-----------------------|----------------------|-------------------|
| `--feed FEED`         | 特定フィードのみ表示 | `--feed aws`      |
| `--min-score N`       | 最小スコア（N以上）  | `--min-score 7`   |
| `--type TYPE`         | 記事タイプでフィルタ | `--type tutorial` |
| `--today`             | 今日の記事のみ       | `--today`         |
| `--week`              | 今週の記事のみ       | `--week`          |
| `--sort {score,date}` | ソート順             | `--sort date`     |

## 🎮 インタラクティブモードの操作

記事を1つずつ表示し、キー操作で移動・管理できます：

### ページャー操作（記事本文表示中）
```
Space / f       : 次のページ
b               : 前のページ
q               : ページャーを終了して操作メニューへ
```

### 基本操作（操作メニュー）
```
[N]ext / Enter  : 次の記事へ（自動で既読マーク ✓）
[P]rev          : 前の記事へ
[L]ist          : 記事リスト表示
[Q]uit          : 終了
数字            : 記事番号で直接移動
```

### 記事管理操作
```
[R]ead          : 既読/未読トグル
[F]avorite      : お気に入りトグル ⭐
[D]elete        : 削除（非表示化）🗑️
[U]ndelete      : 削除解除
```

### 状態アイコン
- `●` : 未読
- `✓` : 既読
- `⭐` : お気に入り

## 💡 使用例

### 例1: 毎日の新着チェック

```bash
# 今日の未読記事を表示
docker-compose run --rm article-viewer --today --unread
```

### 例2: お気に入り記事を再読

```bash
# お気に入り記事のみ表示
docker-compose run --rm article-viewer --favorites
```

### 例3: AWS関連の高評価記事を読む

```bash
# AWS記事でスコア7以上、未読のみ
docker-compose run --rm article-viewer --feed aws --min-score 7 --unread
```

### 例4: チュートリアル記事だけをリスト表示

```bash
# チュートリアル記事のリスト
docker-compose run --rm article-viewer --type tutorial --list-only
```

### 例5: 統計情報を確認

```bash
# どれだけ読んだか確認
docker-compose run --rm article-viewer --stats

# 出力例:
# 📊 記事管理統計
#   既読記事: 15件
#   お気に入り: 3件
#   削除済み: 2件
```

### 例6: 削除した記事を確認・復元

```bash
# 削除済み記事も表示
docker-compose run --rm article-viewer --show-deleted

# インタラクティブモードで [U]キー を押して復元
```

## 💡 Tips

- 記事を開くと**自動で既読マーク**がつきます
- **削除してもファイルは残る**ので安心（非表示化のみ）
- **状態情報**は `shared/storage/article_states.json` に保存されます
- リスト表示で **●** は未読、**✓** は既読、**⭐** はお気に入り

## 🎨 画面表示

```
╭──────────── 📚 記事一覧 (15件) | 未読: 8 | ⭐: 3 ──────────────╮
│  #  │ 状態  │ Feed      │ Title                       │ Score │ Type     │
├─────┼───────┼───────────┼─────────────────────────────┼───────┼──────────┤
│  1  │ ⭐●   │ zenn-llm  │ TransformerのLLMの仕組み     │   8   │ tutorial │
│  2  │ ✓     │ aws       │ Project Rainier online...   │   6   │ news     │
│  3  │ ⭐✓   │ zenn-llm  │ gemma3を使ってみる          │   7   │ tutorial │
╰─────┴───────┴───────────┴─────────────────────────────┴───────┴──────────╯

状態アイコン: ● = 未読 | ✓ = 既読 | ⭐ = お気に入り
### 記事詳細表示

```
╔════════════════════════════════════════════════════════════════╗
║ 📚 記事 1/15  |  ⭐ お気に入り | ● 未読                         ║
║                                                                ║
║ Feed: zenn-llm  |  Score: 8  |  Type: tutorial                ║
║                                                                ║
║ 【図解】ChatGPTなど、TransformerのLLMの仕組み                    ║
║ 🔗 https://zenn.dev/acntechjp/articles/b7a5dab5a27305         ║
║ 👤 Yuta Yamamoto                                              ║
║ 📅 Sun, 09 Nov 2025                                           ║
╚════════════════════════════════════════════════════════════════╝

🎯 この記事の要点
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[記事の内容...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
操作キー:
  [N]ext | [P]rev | [L]ist | [Q]uit | [数字]で直接移動
  [R]ead/Unread | [F]avorite | [D]elete | [U]ndelete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```2  │ aws       │ Project Rainier online, Amazon... │   6   │ news     │
│  3  │ zenn-llm  │ gemma3を使ってみる                 │   7   │ tutorial │
╰─────┴───────┴───────────┴─────────────────────────────┴───────┴──────────╯

状態アイコン: ● = 未読 | ✓ = 既読 | ⭐ = お気に入り
```

### 記事詳細表示

```
╔════════════════════════════════════════════════════════════════╗
║ 📚 記事 1/15  |  ⭐ お気に入り | ● 未読                         ║
║                                                                ║
║ Feed: zenn-llm  |  Score: 8  |  Type: tutorial                ║
║                                                                ║
║ 【図解】ChatGPTなど、TransformerのLLMの仕組み                    ║
║ 🔗 https://zenn.dev/acntechjp/articles/b7a5dab5a27305         ║
║ 👤 Yuta Yamamoto                                              ║
║ 📅 Sun, 09 Nov 2025                                           ║
╚════════════════════════════════════════════════════════════════╝

[本文がページャー（less風）で表示されます]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
操作キー:
  [N]ext | [P]rev | [L]ist | [Q]uit | [数字]で直接移動
  [R]ead/Unread | [F]avorite | [D]elete | [U]ndelete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 🔧 トラブルシューティング

### すべての状態をリセットしたい
```bash
rm shared/storage/article_states.json
```

### 削除した記事を復元したい
```bash
# 削除済み記事も表示
docker-compose run --rm article-viewer --show-deleted

# インタラクティブモードで [U]キー を押して復元
```

## 🗄️ データ保存場所

記事の状態情報は以下のファイルに保存されます：

```
shared/storage/article_states.json
```

JSON形式で以下の情報を管理：
- `read`: 既読記事とタイムスタンプ
- `deleted`: 削除済み記事とタイムスタンプ
- `favorite`: お気に入り記事とタイムスタンプ
- `archived`: アーカイブ記事とタイムスタンプ

このファイルを削除すると、すべての状態がリセットされます。
