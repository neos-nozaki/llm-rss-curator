#!/bin/bash

# LLM RSS Curator - 自動処理パイプライン
# RSS取得 → LLM Judge → Web Scraper → Article Processor を順次実行

set -e  # エラーが発生したら即座に停止

echo "================================================"
echo "🚀 LLM RSS Curator - 自動処理パイプライン開始"
echo "================================================"
echo ""

# 1. RSS Feeder
echo "📡 [1/4] RSS Feeder - 新規記事メタデータ取得中..."
docker-compose run --rm rss-feeder
echo "✅ RSS Feeder 完了"
echo ""

# 2. LLM Judge
echo "🧠 [2/4] LLM Judge - 記事の価値判定 + タイプ分類中..."
docker-compose run --rm llm-judge
echo "✅ LLM Judge 完了"
echo ""

# 3. Web Scraper
echo "🌐 [3/4] Web Scraper - 高評価記事の本文抽出中..."
docker-compose run --rm web-scraper
echo "✅ Web Scraper 完了"
echo ""

# 4. Article Processor
echo "📝 [4/4] Article Processor - 要約・解説生成中..."
docker-compose run --rm llm-processor
echo "✅ Article Processor 完了"
echo ""

echo "================================================"
echo "🎉 すべての処理が完了しました！"
echo "================================================"
echo ""
echo "📖 記事を読むには:"
echo "   docker-compose run --rm article-viewer"
echo ""
