#!/usr/bin/env python3
"""
フィルタリングエラーで score=0 になった記事のフィルタ結果をリセット
"""
import json
from pathlib import Path

storage_path = Path('shared/storage/rss-feeds')
reset_count = 0

for feed_dir in storage_path.iterdir():
    if not feed_dir.is_dir():
        continue
    
    for json_file in feed_dir.glob('*.json'):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # filter_score が 0 の場合のみリセット
        if data.get('filter_score') == 0:
            # フィルタ関連フィールドを削除
            data.pop('filter_score', None)
            data.pop('filter_reason', None)
            data.pop('interest_match', None)
            data.pop('article_type', None)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"リセット: {feed_dir.name}/{json_file.stem}")
            reset_count += 1

print(f"\n合計 {reset_count} 件の記事をリセットしました")
print("再度 LLM Judge を実行してください: docker-compose run --rm llm-judge")
