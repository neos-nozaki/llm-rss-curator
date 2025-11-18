#!/usr/bin/env python3
"""
記事状態管理システム - 既読・未読・削除・お気に入りを管理
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional


class ArticleStateManager:
    """記事の状態（既読・未読・削除・お気に入り）を管理"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.state_file = self.storage_path / 'article_states.json'
        self.states = self._load_states()
    
    def _load_states(self) -> Dict:
        """状態ファイルを読み込み"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'read': {},        # article_id: timestamp
            'deleted': {},     # article_id: timestamp
            'favorite': {},    # article_id: timestamp
            'archived': {}     # article_id: timestamp
        }
    
    def _save_states(self):
        """状態ファイルに保存"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.states, f, indent=2, ensure_ascii=False)
    
    def mark_as_read(self, article_id: str):
        """既読にする"""
        self.states['read'][article_id] = datetime.now().isoformat()
        self._save_states()
    
    def mark_as_unread(self, article_id: str):
        """未読にする（既読マークを削除）"""
        if article_id in self.states['read']:
            del self.states['read'][article_id]
            self._save_states()
    
    def mark_as_deleted(self, article_id: str):
        """削除マークをつける"""
        self.states['deleted'][article_id] = datetime.now().isoformat()
        self._save_states()
    
    def undelete(self, article_id: str):
        """削除マークを解除"""
        if article_id in self.states['deleted']:
            del self.states['deleted'][article_id]
            self._save_states()
    
    def toggle_favorite(self, article_id: str):
        """お気に入りをトグル"""
        if article_id in self.states['favorite']:
            del self.states['favorite'][article_id]
        else:
            self.states['favorite'][article_id] = datetime.now().isoformat()
        self._save_states()
    
    def archive(self, article_id: str):
        """アーカイブする"""
        self.states['archived'][article_id] = datetime.now().isoformat()
        self._save_states()
    
    def is_read(self, article_id: str) -> bool:
        """既読かどうか"""
        return article_id in self.states['read']
    
    def is_deleted(self, article_id: str) -> bool:
        """削除済みかどうか"""
        return article_id in self.states['deleted']
    
    def is_favorite(self, article_id: str) -> bool:
        """お気に入りかどうか"""
        return article_id in self.states['favorite']
    
    def is_archived(self, article_id: str) -> bool:
        """アーカイブ済みかどうか"""
        return article_id in self.states['archived']
    
    def get_unread_ids(self) -> Set[str]:
        """未読記事IDのセットを取得"""
        all_ids = set()
        # 実際には全記事IDを取得する必要がある
        return all_ids - set(self.states['read'].keys())
    
    def get_read_ids(self) -> Set[str]:
        """既読記事IDのセットを取得"""
        return set(self.states['read'].keys())
    
    def get_deleted_ids(self) -> Set[str]:
        """削除済み記事IDのセットを取得"""
        return set(self.states['deleted'].keys())
    
    def get_favorite_ids(self) -> Set[str]:
        """お気に入り記事IDのセットを取得"""
        return set(self.states['favorite'].keys())
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return {
            'read_count': len(self.states['read']),
            'deleted_count': len(self.states['deleted']),
            'favorite_count': len(self.states['favorite']),
            'archived_count': len(self.states['archived'])
        }
