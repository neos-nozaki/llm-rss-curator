#!/usr/bin/env python3
"""
Web Scraper - URLから記事本文を抽出してMarkdown形式でストレージに保存
"""
import os
import json
import logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import html2text
import time

# ロギング設定
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.rss_feeds_dir = self.storage_path / 'rss-feeds'
        self.scraped_dir = self.storage_path / 'scraped-articles'
        self.scraped_dir.mkdir(parents=True, exist_ok=True)
        
        self.timeout = int(os.getenv('TIMEOUT_SECONDS', '30'))
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (compatible; RSSBot/1.0)')
        
        # html2text設定
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.ignore_emphasis = False
        self.h2t.body_width = 0  # 改行を自動挿入しない
    
    def get_pending_articles(self) -> list:
        """スクレイピング待ちの記事を取得"""
        pending = []
        
        if not self.rss_feeds_dir.exists():
            return pending
        
        for feed_dir in self.rss_feeds_dir.iterdir():
            if not feed_dir.is_dir():
                continue
            
            feed_name = feed_dir.name
            
            for metadata_file in feed_dir.glob('*.json'):
                article_id = metadata_file.stem
                
                # 既にスクレイピング済みかチェック（.mdファイル）
                scraped_file = self.scraped_dir / feed_name / f"{article_id}.md"
                if scraped_file.exists():
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # フィルタリングスコアをチェック（設定されている場合のみ）
                if 'filter_score' in metadata:
                    # user_preferences.jsonから閾値を取得
                    filter_config_path = Path(__file__).parent.parent / 'llm-judge' / 'config' / 'user_preferences.json'
                    if filter_config_path.exists():
                        with open(filter_config_path, 'r', encoding='utf-8') as f:
                            user_prefs = json.load(f)
                            threshold = float(user_prefs.get('score_threshold', 6.0))
                    else:
                        threshold = 6.0
                    
                    if metadata['filter_score'] < threshold:
                        logger.debug(f"スキップ（スコア不足: {metadata['filter_score']}）: {article_id}")
                        continue
                
                pending.append({
                    'feed_name': feed_name,
                    'article_id': article_id,
                    'metadata': metadata
                })
        
        return pending
    
    def extract_article_text(self, url: str) -> str:
        """URLから記事本文をMarkdown形式で抽出"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 不要な要素を除去
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                element.decompose()
            
            # 記事本文を抽出（一般的なタグを優先）
            article_html = ''
            
            # よくある記事コンテナを試す
            article = soup.find('article')
            if article:
                article_html = str(article)
            else:
                # mainタグを試す
                main = soup.find('main')
                if main:
                    article_html = str(main)
                else:
                    # フォールバック: body全体
                    body = soup.find('body')
                    if body:
                        article_html = str(body)
            
            # HTMLをMarkdownに変換
            if article_html:
                markdown_text = self.h2t.handle(article_html)
                # 余分な空行を削除
                lines = [line for line in markdown_text.split('\n')]
                # 連続する空行を1つにまとめる
                cleaned_lines = []
                prev_empty = False
                for line in lines:
                    is_empty = line.strip() == ''
                    if is_empty and prev_empty:
                        continue
                    cleaned_lines.append(line)
                    prev_empty = is_empty
                
                return '\n'.join(cleaned_lines)
            
            return ""
            
        except Exception as e:
            logger.error(f"スクレイピングエラー ({url}): {e}")
            return ""
    
    def save_article_text(self, feed_name: str, article_id: str, text: str):
        """記事本文をMarkdown形式で保存"""
        feed_dir = self.scraped_dir / feed_name
        feed_dir.mkdir(parents=True, exist_ok=True)
        
        article_path = feed_dir / f"{article_id}.md"
        
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"保存完了: {feed_name}/{article_id}.md ({len(text)} chars)")
    
    def run(self):
        """メイン処理"""
        logger.info("=== Webスクレイパー開始 ===")
        
        articles = self.get_pending_articles()
        logger.info(f"スクレイピング対象: {len(articles)}件")
        
        if not articles:
            logger.info("スクレイピング対象なし")
            return
        
        scraped_count = 0
        
        for article in articles:
            feed_name = article['feed_name']
            article_id = article['article_id']
            metadata = article['metadata']
            
            url = metadata.get('url', metadata.get('link', ''))
            if not url:
                logger.warning(f"URLなし: {feed_name}/{article_id}")
                continue
            
            logger.info(f"スクレイピング中: {url}")
            
            text = self.extract_article_text(url)
            if text:
                self.save_article_text(feed_name, article_id, text)
                scraped_count += 1
            else:
                logger.warning(f"テキスト抽出失敗: {url}")
            
            # レート制限対策
            time.sleep(1)
        
        logger.info(f"=== スクレイピング完了: {scraped_count}件 ===")


def main(event=None, context=None):
    """メインエントリポイント（ローカル実行・Lambda両対応）"""
    storage_path = os.getenv('STORAGE_PATH', '/tmp/rss-data')
    
    scraper = WebScraper(storage_path)
    scraper.run()
    
    return {'statusCode': 200, 'body': 'Web scraping completed'}


# AWS Lambda互換性のためのエイリアス
lambda_handler = main

if __name__ == '__main__':
    main()
