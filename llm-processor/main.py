#!/usr/bin/env python3
"""
Article Processor - 記事本文を解説・要約してストレージに保存
"""
import os
import json
import logging
from pathlib import Path
from openai import OpenAI

# ロギング設定
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArticleProcessor:
    def __init__(self, storage_path: str, api_key: str):
        self.storage_path = Path(storage_path)
        self.rss_feeds_dir = self.storage_path / 'rss-feeds'
        self.scraped_dir = self.storage_path / 'scraped-articles'
        self.summaries_dir = self.storage_path / 'processed-articles'
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('ARTICLE_MODEL', 'gpt-4o')
        
        # プロンプトディレクトリのパスを保持（動的読み込み用）
        self.prompts_dir = Path(__file__).parent / 'prompts'
        
        # システムプロンプトは共通なので事前に読み込み
        with open(self.prompts_dir / 'system.txt', 'r', encoding='utf-8') as f:
            self.system_prompt = f.read().strip()
    
    def get_pending_articles(self) -> list:
        """要約待ちの記事を取得"""
        pending = []
        
        if not self.scraped_dir.exists():
            return pending
        
        for feed_dir in self.scraped_dir.iterdir():
            if not feed_dir.is_dir():
                continue
            
            feed_name = feed_dir.name
            
            for text_file in feed_dir.glob('*.md'):  # .md形式に変更
                article_id = text_file.stem
                
                # 既に要約済みかチェック
                summary_file = self.summaries_dir / feed_name / f"{article_id}.md"
                if summary_file.exists():
                    continue
                
                # メタデータを取得
                metadata_file = self.rss_feeds_dir / feed_name / f"{article_id}.json"
                if not metadata_file.exists():
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                with open(text_file, 'r', encoding='utf-8') as f:
                    article_text = f.read()
                
                pending.append({
                    'feed_name': feed_name,
                    'article_id': article_id,
                    'metadata': metadata,
                    'text': article_text
                })
        
        return pending
    
    def create_summary_prompt(self, article_text: str, metadata: dict) -> str:
        """要約用のプロンプトを生成（article_typeに応じて動的に読み込み）"""
        article_type = metadata.get('article_type', 'tutorial')
        
        # article_typeに応じたプロンプトファイルを動的に読み込み
        prompt_filename = f'user_{article_type}.txt'
        prompt_path = self.prompts_dir / prompt_filename
        
        if not prompt_path.exists():
            logger.warning(f"プロンプトファイルが見つかりません: {prompt_filename}、デフォルト(tutorial)を使用")
            prompt_path = self.prompts_dir / 'user_tutorial.txt'
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read().strip()
        
        # テンプレートに値を埋め込み
        return template.format(
            title=metadata.get('title', 'N/A'),
            content=article_text[:8000]  # トークン制限対策
        )
    
    def generate_summary(self, article_text: str, metadata: dict) -> str:
        """GPT-4oで要約を生成（article_typeに応じてmax_tokensを調整）"""
        try:
            article_type = metadata.get('article_type', 'tutorial')
            prompt = self.create_summary_prompt(article_text, metadata)
            
            # article_typeに応じてmax_tokensを調整
            max_tokens = 800 if article_type == 'news' else 2000
            
            # Response API: client.responses.create() with input parameter
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_output_tokens=max_tokens,
                stream=False
            )
            
            # output_textプロパティからテキストを取得
            summary = response.output_text
            
            # マークダウンコードブロックを除去（必要に応じて）
            if summary.startswith('```'):
                summary = summary.split('\n', 1)[1] if '\n' in summary else summary
                if summary.endswith('```'):
                    summary = summary.rsplit('```', 1)[0]
                summary = summary.strip()
            
            logger.info(f"要約生成完了 (type: {article_type}, tokens: {max_tokens})")
            return summary
            
        except Exception as e:
            logger.error(f"要約生成エラー: {str(e)}")
            return ''
    
    def save_summary(self, feed_name: str, article_id: str, summary: str, metadata: dict):
        """要約をMarkdownファイルとして保存"""
        feed_dir = self.summaries_dir / feed_name
        feed_dir.mkdir(parents=True, exist_ok=True)
        
        summary_path = feed_dir / f"{article_id}.md"
        
        # メタデータヘッダーを追加
        header = f"""---
title: {metadata.get('title', 'N/A')}
url: {metadata.get('url', 'N/A')}
author: {metadata.get('author', 'N/A')}
published: {metadata.get('published', 'N/A')}
feed: {feed_name}
---

"""
        
        full_content = header + summary
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        logger.info(f"保存完了: {feed_name}/{article_id}.md")
    
    def process_article(self, article_info: dict):
        """記事を要約"""
        feed_name = article_info['feed_name']
        article_id = article_info['article_id']
        metadata = article_info['metadata']
        article_text = article_info['text']
        
        logger.info(f"要約開始: {metadata.get('title', article_id)}")
        
        summary = self.generate_summary(article_text, metadata)
        
        if summary:
            self.save_summary(feed_name, article_id, summary, metadata)
        else:
            logger.warning(f"要約生成失敗: {article_id}")
    
    def run(self):
        """全ての待機記事を処理"""
        pending = self.get_pending_articles()
        logger.info(f"処理開始: {len(pending)}件の記事")
        
        for article_info in pending:
            self.process_article(article_info)
        
        logger.info(f"処理完了: {len(pending)}件")


def main():
    storage_path = os.getenv('STORAGE_PATH', './storage')
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("OPENAI_API_KEY が設定されていません")
        return
    
    processor = ArticleProcessor(storage_path, api_key)
    processor.run()


if __name__ == '__main__':
    main()
