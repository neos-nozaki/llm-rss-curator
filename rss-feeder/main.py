#!/usr/bin/env python3
"""
RSS Feeder - RSSフィードから新規記事を取得してストレージに保存
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import feedparser
import hashlib
import time
from email.utils import parsedate_to_datetime

# ロギング設定
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSSFeeder:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.rss_feeds_dir = self.storage_path / 'rss-feeds'
        self.rss_feeds_dir.mkdir(parents=True, exist_ok=True)
        self.max_articles = int(os.getenv('MAX_ARTICLES_PER_FEED', '10'))
        self.retention_days = int(os.getenv('RETENTION_DAYS', '7'))
        self.max_article_age_days = int(os.getenv('MAX_ARTICLE_AGE_DAYS', '3'))  # 新規: 取得対象の最大経過日数
        
    def load_feed_config(self) -> list:
        """フィード設定を読み込む"""
        config_path = Path(__file__).parent / 'config' / 'feeds.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return [feed for feed in config['feeds'] if feed.get('enabled', True)]
    
    def generate_article_id(self, url: str) -> str:
        """URLから一意なIDを生成"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def article_exists(self, feed_name: str, article_id: str) -> bool:
        """既に処理済みの記事かチェック"""
        article_path = self.rss_feeds_dir / feed_name / f"{article_id}.json"
        return article_path.exists()
    
    def save_article_metadata(self, feed_name: str, article_data: dict):
        """記事メタデータを保存"""
        feed_dir = self.rss_feeds_dir / feed_name
        feed_dir.mkdir(parents=True, exist_ok=True)
        
        article_id = article_data['id']
        article_path = feed_dir / f"{article_id}.json"
        
        with open(article_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存完了: {feed_name}/{article_id}.json")
    
    def cleanup_old_articles_by_date(self):
        """指定日数より古い記事を全フィードから削除"""
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)
        total_deleted = 0
        
        logger.info(f"古いファイルをクリーンアップ: {self.retention_days}日以前のファイルを削除")
        
        # 全フィードをスキャン
        if not self.rss_feeds_dir.exists():
            return
        
        for feed_dir in self.rss_feeds_dir.iterdir():
            if not feed_dir.is_dir():
                continue
            
            feed_name = feed_dir.name
            deleted_count = 0
            
            # メタデータファイルをスキャン
            for metadata_file in feed_dir.glob('*.json'):
                if metadata_file.stat().st_mtime < cutoff_time:
                    article_id = metadata_file.stem
                    
                    # 関連する全ファイルを削除（メタデータ、本文、要約を一括削除）
                    scraped_file = self.storage_path / 'scraped-articles' / feed_name / f"{article_id}.md"
                    summary_file = self.storage_path / 'article-summaries' / feed_name / f"{article_id}.md"
                    
                    try:
                        metadata_file.unlink()  # メタデータ削除
                        if scraped_file.exists():
                            scraped_file.unlink()  # 本文削除
                        if summary_file.exists():
                            summary_file.unlink()  # 要約削除
                        deleted_count += 1
                        logger.debug(f"削除 ({feed_name}): {article_id} (メタデータ + 本文 + 要約)")
                    except Exception as e:
                        logger.error(f"削除エラー ({feed_name}/{article_id}): {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"削除完了 ({feed_name}): {deleted_count}件")
                total_deleted += deleted_count
        
        if total_deleted > 0:
            logger.info(f"クリーンアップ完了: 合計 {total_deleted}件削除")
    
    def cleanup_old_articles(self, feed_name: str):
        """古い記事を削除して最新N件だけ保持"""
        feed_dir = self.rss_feeds_dir / feed_name
        if not feed_dir.exists():
            return
        
        # すべての記事ファイルを取得
        article_files = list(feed_dir.glob('*.json'))
        
        if len(article_files) <= self.max_articles:
            return  # 削除不要
        
        # 更新日時でソート（新しい順）
        article_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # 古いファイルを削除
        files_to_delete = article_files[self.max_articles:]
        deleted_count = 0
        
        for file_path in files_to_delete:
            article_id = file_path.stem
            
            # 関連する全ファイルを削除（scraped, summary も）
            scraped_file = self.storage_path / 'scraped-articles' / feed_name / f"{article_id}.txt"
            summary_file = self.storage_path / 'article-summaries' / feed_name / f"{article_id}.md"
            
            try:
                file_path.unlink()  # メタデータ削除
                if scraped_file.exists():
                    scraped_file.unlink()
                if summary_file.exists():
                    summary_file.unlink()
                deleted_count += 1
                logger.debug(f"削除: {article_id}")
            except Exception as e:
                logger.error(f"削除エラー: {article_id} - {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"古い記事を削除: {feed_name} - {deleted_count}件")
    
    def fetch_feed(self, feed_config: dict) -> int:
        """フィードを取得して新規記事を保存"""
        feed_name = feed_config['name']
        feed_url = feed_config['url']
        
        logger.info(f"フィード取得開始: {feed_name} ({feed_url})")
        
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"フィードパースに問題: {feed_name}")
            
            new_articles = 0
            cutoff_date = datetime.now() - timedelta(days=self.max_article_age_days)
            
            for entry in feed.entries:
                article_url = entry.get('link', '')
                if not article_url:
                    continue
                
                # 記事の公開日をチェック（古すぎる記事はスキップ）
                published_str = entry.get('published', '')
                if published_str:
                    try:
                        # RFC 2822形式をパース（例: "Thu, 19 Jan 2017 08:00:00 GMT"）
                        published_date = parsedate_to_datetime(published_str)
                        if published_date < cutoff_date.replace(tzinfo=published_date.tzinfo):
                            logger.debug(f"スキップ（古い記事: {published_date.date()}）: {entry.get('title', 'No Title')[:50]}")
                            continue
                    except Exception as e:
                        logger.debug(f"日付パースエラー（{published_str}）: {e}")
                        # パースできない場合は取得を続行
                
                article_id = self.generate_article_id(article_url)
                
                # 既存チェック
                if self.article_exists(feed_name, article_id):
                    logger.debug(f"スキップ（既存）: {article_id}")
                    continue
                
                # メタデータ抽出
                article_data = {
                    'id': article_id,
                    'feed_name': feed_name,
                    'title': entry.get('title', 'No Title'),
                    'url': article_url,
                    'published': entry.get('published', ''),
                    'author': entry.get('author', ''),
                    'summary': entry.get('summary', ''),
                    'fetched_at': datetime.now().isoformat()
                }
                
                self.save_article_metadata(feed_name, article_data)
                new_articles += 1
            
            # 古い記事を削除（件数制限）
            self.cleanup_old_articles(feed_name)
            
            logger.info(f"完了: {feed_name} - 新規記事 {new_articles}件")
            return new_articles
            
        except Exception as e:
            logger.error(f"エラー発生: {feed_name} - {str(e)}")
            return 0
    
    def run(self):
        """全フィードを処理"""
        feeds = self.load_feed_config()
        logger.info(f"処理開始: {len(feeds)}個のフィード")
        
        # 古いファイルを先にクリーンアップ（日数ベース）
        self.cleanup_old_articles_by_date()
        
        total_new = 0
        for feed_config in feeds:
            new_count = self.fetch_feed(feed_config)
            total_new += new_count
        
        logger.info(f"全体完了: 合計 {total_new}件の新規記事")


def main():
    storage_path = os.getenv('STORAGE_PATH', './storage')
    feeder = RSSFeeder(storage_path)
    feeder.run()


if __name__ == '__main__':
    main()
