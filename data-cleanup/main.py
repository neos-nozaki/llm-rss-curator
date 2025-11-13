#!/usr/bin/env python3
"""
Data Cleanup - 古いデータを一括削除
retention_daysを超過した記事データを全削除（メタデータ・本文・要約）
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# ロギング設定
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCleanup:
    def __init__(self, storage_path: str, retention_days: int):
        self.storage_path = Path(storage_path)
        self.retention_days = retention_days
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        logger.info(f"保持期間: {retention_days}日")
        logger.info(f"削除基準日時: {self.cutoff_date.isoformat()}")
    
    def get_old_articles(self) -> list:
        """retention_daysを超過した記事を取得"""
        old_articles = []
        rss_feeds_dir = self.storage_path / 'rss-feeds'
        
        if not rss_feeds_dir.exists():
            return old_articles
        
        for feed_dir in rss_feeds_dir.iterdir():
            if not feed_dir.is_dir():
                continue
            
            feed_name = feed_dir.name
            
            for metadata_file in feed_dir.glob('*.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # published日時をチェック
                    published_str = metadata.get('published', '')
                    if not published_str:
                        logger.warning(f"published フィールドなし: {metadata_file}")
                        continue
                    
                    # ISO 8601形式をパース
                    published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    
                    # タイムゾーン情報を削除して比較
                    published_date = published_date.replace(tzinfo=None)
                    
                    if published_date < self.cutoff_date:
                        article_id = metadata_file.stem
                        old_articles.append({
                            'feed_name': feed_name,
                            'article_id': article_id,
                            'published': published_str
                        })
                
                except Exception as e:
                    logger.error(f"メタデータ読み込みエラー ({metadata_file}): {e}")
        
        return old_articles
    
    def delete_article_data(self, feed_name: str, article_id: str) -> dict:
        """記事の全データを削除（メタデータ・本文・要約）"""
        deleted = {
            'metadata': False,
            'scraped': False,
            'summary': False
        }
        
        # 1. メタデータ削除
        metadata_path = self.storage_path / 'rss-feeds' / feed_name / f"{article_id}.json"
        if metadata_path.exists():
            metadata_path.unlink()
            deleted['metadata'] = True
            logger.debug(f"削除: {metadata_path}")
        
        # 2. スクレイピング済み記事削除
        scraped_path = self.storage_path / 'scraped-articles' / feed_name / f"{article_id}.md"
        if scraped_path.exists():
            scraped_path.unlink()
            deleted['scraped'] = True
            logger.debug(f"削除: {scraped_path}")
        
        # 3. 要約記事削除
        summary_path = self.storage_path / 'processed-articles' / feed_name / f"{article_id}.md"
        if summary_path.exists():
            summary_path.unlink()
            deleted['summary'] = True
            logger.debug(f"削除: {summary_path}")
        
        return deleted
    
    def run(self, dry_run: bool = False):
        """メイン処理"""
        logger.info("=== データクリーンアップ開始 ===")
        
        old_articles = self.get_old_articles()
        logger.info(f"削除対象: {len(old_articles)}件")
        
        if not old_articles:
            logger.info("削除対象なし")
            return
        
        if dry_run:
            logger.info("【ドライランモード】実際の削除は行いません")
            for article in old_articles:
                logger.info(f"[削除予定] {article['feed_name']}/{article['article_id']} (published: {article['published']})")
            return
        
        deleted_count = 0
        total_files = 0
        
        for article in old_articles:
            feed_name = article['feed_name']
            article_id = article['article_id']
            
            deleted = self.delete_article_data(feed_name, article_id)
            
            files_deleted = sum(deleted.values())
            if files_deleted > 0:
                deleted_count += 1
                total_files += files_deleted
                logger.info(f"削除完了: {feed_name}/{article_id} ({files_deleted}ファイル)")
        
        logger.info(f"=== クリーンアップ完了: {deleted_count}記事、{total_files}ファイル削除 ===")


def main(event=None, context=None):
    """エントリポイント"""
    storage_path = os.getenv('STORAGE_PATH', '/tmp/rss-data')
    retention_days = int(os.getenv('RETENTION_DAYS', '7'))
    dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
    
    cleanup = DataCleanup(storage_path, retention_days)
    cleanup.run(dry_run=dry_run)
    
    return {'statusCode': 200, 'body': 'Data cleanup completed'}


if __name__ == '__main__':
    main()
