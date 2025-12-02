#!/usr/bin/env python3
"""
RSS Filter - LLMで記事の価値を判定し、要約対象を選別
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


class RSSFilter:
    def __init__(self, storage_path: str, api_key: str):
        self.storage_path = Path(storage_path)
        self.rss_feeds_dir = self.storage_path / 'rss-feeds'
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('FILTER_MODEL', 'gpt-4o-mini')
        
        # プロンプトファイルを読み込み
        prompts_dir = Path(__file__).parent / 'prompts'
        with open(prompts_dir / 'system.txt', 'r', encoding='utf-8') as f:
            self.system_prompt = f.read().strip()
        with open(prompts_dir / 'user.txt', 'r', encoding='utf-8') as f:
            self.user_prompt_template = f.read().strip()
        with open(prompts_dir / 'response_schema.json', 'r', encoding='utf-8') as f:
            self.response_schema = json.load(f)
        
        # ユーザー設定を読み込み（デフォルト値で疎結合を保つ）
        config_dir = Path(__file__).parent / 'config'
        with open(config_dir / 'user_preferences.json', 'r', encoding='utf-8') as f:
            self.user_prefs = json.load(f)
            self.score_threshold = float(self.user_prefs.get('score_threshold', 6.0))
    
    def get_unfiltered_articles(self) -> list:
        """フィルタリング待ちの記事を取得"""
        unfiltered = []
        
        if not self.rss_feeds_dir.exists():
            return unfiltered
        
        for feed_dir in self.rss_feeds_dir.iterdir():
            if not feed_dir.is_dir():
                continue
            
            feed_name = feed_dir.name
            
            for metadata_file in feed_dir.glob('*.json'):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 既にフィルタリング済みかチェック
                if 'filter_score' in metadata:
                    continue
                
                unfiltered.append({
                    'feed_name': feed_name,
                    'article_id': metadata_file.stem,
                    'metadata': metadata
                })
        
        return unfiltered
    
    def create_filter_prompt(self, title: str, summary: str) -> str:
        """フィルタリング用のプロンプトを生成（スキーマから指示を自動生成）"""
        # スキーマから回答指示を自動生成
        response_instructions = self._generate_response_instructions()
        
        # ユーザーの興味を優先度順に整形
        user_interests = self._format_user_interests()
        
        # 評価基準を整形
        evaluation_criteria = self._format_evaluation_criteria()
        
        # テンプレートに値を埋め込み
        return self.user_prompt_template.format(
            user_interests=user_interests,
            evaluation_criteria=evaluation_criteria,
            title=title,
            summary=summary,
            response_instructions=response_instructions
        )
    
    def _format_user_interests(self) -> str:
        """ユーザーの興味を優先度順に整形"""
        interests = self.user_prefs.get('interests', [])
        if not interests:
            return "特になし"
        
        lines = []
        for item in interests:
            if isinstance(item, dict):
                topic = item.get('topic', '')
                priority = item.get('priority', '?')
                note = item.get('note', '')
                lines.append(f"{priority}. {topic}")
                if note:
                    lines.append(f"   → {note}")
            else:
                lines.append(f"- {item}")
        
        return '\n'.join(lines)
    
    def _format_evaluation_criteria(self) -> str:
        """評価基準を整形"""
        criteria = self.user_prefs.get('evaluation_criteria', {})
        if not criteria:
            return ""
        
        lines = []
        
        # 必須要件
        critical = criteria.get('critical_requirements', [])
        if critical:
            lines.append("【必須要件】")
            for req in critical:
                lines.append(f"✓ {req}")
            lines.append("")
        
        # 除外基準
        exclusions = criteria.get('exclusions', [])
        if exclusions:
            lines.append("【除外対象（これらは低スコア）】")
            for exc in exclusions:
                lines.append(f"✗ {exc}")
            lines.append("")
        
        # スコアリング基準
        for score_level in ['high_score', 'medium_score', 'low_score']:
            if score_level in criteria:
                level_data = criteria[score_level]
                range_str = level_data.get('range', '')
                desc = level_data.get('description', '')
                
                label_map = {
                    'high_score': '高スコア',
                    'medium_score': '中スコア',
                    'low_score': '低スコア'
                }
                label = label_map.get(score_level, score_level)
                
                lines.append(f"【{label}（{range_str}）】")
                lines.append(desc)
                lines.append("")
        
        return '\n'.join(lines).strip()
    
    def _generate_response_instructions(self) -> str:
        """JSONスキーマから回答指示を自動生成"""
        properties = self.response_schema.get('properties', {})
        required = self.response_schema.get('required', [])
        
        instructions = "以下のJSON形式で**必ず**回答してください：\n\n**必須フィールド:**\n"
        
        for field in required:
            field_info = properties.get(field, {})
            field_type = field_info.get('type', 'string')
            description = field_info.get('description', '')
            
            # 型に応じた説明
            type_hint = ""
            if field_type == "integer":
                type_hint = "（整数）"
            elif field_type == "number":
                type_hint = "（数値）"
            elif field_type == "boolean":
                type_hint = "（true/false）"
            elif field_type == "array":
                type_hint = "（配列）"
            elif field_type == "object":
                type_hint = "（オブジェクト）"
            
            instructions += f"- `{field}` {type_hint}: {description}\n"
            
            # 例があれば追加
            if 'example' in field_info:
                instructions += f"  - 例: `{json.dumps(field_info['example'], ensure_ascii=False)}`\n"
        
        # オプションフィールド
        optional_fields = [k for k in properties.keys() if k not in required]
        if optional_fields:
            instructions += "\n**オプションフィールド:**\n"
            for field in optional_fields:
                field_info = properties.get(field, {})
                description = field_info.get('description', '')
                instructions += f"- `{field}`: {description}\n"
        
        return instructions
    
    def filter_article(self, title: str, summary: str) -> dict:
        """記事をLLMでフィルタリング"""
        user_prompt = self.create_filter_prompt(title, summary)
        
        try:
            # Response API: client.responses.create() with input parameter
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                modalities=["text"],
                temperature=0.3,
                stream=False
            )
            
            # Response APIでは response.output[0].content[0].text でテキストを取得
            result_text = response.output[0].content[0].text
            result = json.loads(result_text)
            logger.info(f"フィルタリング完了: スコア={result.get('score', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"フィルタリングエラー: {e}")
            return {
                "score": 0,
                "reason": f"エラー: {str(e)}",
                "interest_match": []
            }
    
    def save_filter_result(self, feed_name: str, article_id: str, filter_result: dict, metadata: dict):
        """フィルタリング結果をメタデータに保存"""
        metadata_path = self.rss_feeds_dir / feed_name / f"{article_id}.json"
        
        metadata['filter_score'] = filter_result.get('score', 0)
        metadata['filter_reason'] = filter_result.get('reason', '')
        metadata['interest_match'] = filter_result.get('interest_match', [])
        metadata['article_type'] = filter_result.get('article_type', 'tutorial')  # デフォルトはtutorial
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"フィルタ結果保存: {feed_name}/{article_id}.json (type: {metadata['article_type']})")
    
    def run(self):
        """メイン処理"""
        logger.info("=== RSSフィルター開始 ===")
        
        articles = self.get_unfiltered_articles()
        logger.info(f"フィルタリング対象: {len(articles)}件")
        
        if not articles:
            logger.info("フィルタリング対象なし")
            return
        
        filtered_count = 0
        high_score_count = 0
        
        for article in articles:
            feed_name = article['feed_name']
            article_id = article['article_id']
            metadata = article['metadata']
            
            title = metadata.get('title', '')
            summary = metadata.get('summary', '')
            
            logger.info(f"フィルタリング中: {feed_name}/{article_id}")
            
            filter_result = self.filter_article(title, summary)
            self.save_filter_result(feed_name, article_id, filter_result, metadata)
            
            filtered_count += 1
            score = filter_result.get('score', 0)
            if score >= self.score_threshold:
                high_score_count += 1
                logger.info(f"✅ 高スコア記事: {title} (スコア: {score})")
        
        logger.info(f"=== フィルタリング完了: {filtered_count}件処理、{high_score_count}件が閾値以上 ===")


def main(event=None, context=None):
    """メインエントリポイント（ローカル実行・Lambda両対応）"""
    storage_path = os.getenv('STORAGE_PATH', '/tmp/rss-data')
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("OPENAI_API_KEY が設定されていません")
        return {'statusCode': 500, 'body': 'API Key not configured'}
    
    filter_service = RSSFilter(storage_path, api_key)
    filter_service.run()
    
    return {'statusCode': 200, 'body': 'RSS filtering completed'}


# AWS Lambda互換性のためのエイリアス
lambda_handler = main

if __name__ == '__main__':
    main()
