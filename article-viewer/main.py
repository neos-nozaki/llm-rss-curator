#!/usr/bin/env python3
"""
Article Viewer - 処理済み記事を読みやすく表示
"""
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
from article_state import ArticleStateManager

console = Console()


class ArticleViewer:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.processed_dir = self.storage_path / 'processed-articles'
        self.metadata_dir = self.storage_path / 'rss-feeds'
        self.state_manager = ArticleStateManager(storage_path)
    def load_articles(self, 
                     feed: Optional[str] = None,
                     min_score: Optional[float] = None,
                     article_type: Optional[str] = None,
                     since_date: Optional[datetime] = None,
                     show_deleted: bool = False,
                     unread_only: bool = False,
                     favorites_only: bool = False) -> List[Dict]:
        """記事を読み込み、フィルタリング"""
        articles = []
        
        if not self.processed_dir.exists():
            return articles
        
        # フィード名のリストを取得
        feeds = [feed] if feed else [d.name for d in self.processed_dir.iterdir() if d.is_dir()]
        
        for feed_name in feeds:
            feed_dir = self.processed_dir / feed_name
            if not feed_dir.exists():
                continue
            
            for md_file in feed_dir.glob('*.md'):
                article_id = md_file.stem
                
                # メタデータを読み込み
                metadata_file = self.metadata_dir / feed_name / f"{article_id}.json"
                if not metadata_file.exists():
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # フィルタリング
                score = metadata.get('filter_score', 0)
                if min_score and score < min_score:
                    continue
                
                if article_type and metadata.get('article_type') != article_type:
                    continue
                
                # 日付フィルタ
                if since_date:
                    processed_at = metadata.get('processed_at')
                    if processed_at:
                        article_date = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                        if article_date < since_date:
                            continue
                
                # 状態フィルタ
                if not show_deleted and self.state_manager.is_deleted(article_id):
                    continue
                
                if unread_only and self.state_manager.is_read(article_id):
                    continue
                
                if favorites_only and not self.state_manager.is_favorite(article_id):
                    continue
                
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # YAMLフロントマターを除去
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                
                articles.append({
                    'feed_name': feed_name,
                    'article_id': article_id,
                    'metadata': metadata,
                    'content': content,
                    'file_path': md_file,
                    'is_read': self.state_manager.is_read(article_id),
                    'is_deleted': self.state_manager.is_deleted(article_id),
                    'is_favorite': self.state_manager.is_favorite(article_id)
                })
        
        return articles
    
    def display_article_list(self, articles: List[Dict], sort_by: str = 'score'):
        """記事一覧を表示"""
        # 統計情報を表示
        stats = self.state_manager.get_stats()
        unread_count = len([a for a in articles if not a['is_read']])
        
        table = Table(
            title=f"📚 記事一覧 ({len(articles)}件) | 未読: {unread_count} | ⭐: {stats['favorite_count']}",
            box=box.ROUNDED,
            show_lines=False
        )
        table.add_column("#", style="cyan", width=4, no_wrap=True)
        table.add_column("状態", style="yellow", width=4, no_wrap=True)
        table.add_column("Feed", style="magenta", width=10, no_wrap=True)
        table.add_column("タイトル", style="white", width=50, no_wrap=True)
        table.add_column("Score", style="green", width=5, no_wrap=True)
        table.add_column("Type", style="blue", width=8, no_wrap=True)
        
        for idx, article in enumerate(articles, 1):
            metadata = article['metadata']
            title = metadata.get('title', 'No Title')
            # タイトルを50文字に制限
            if len(title) > 47:
                title = title[:47] + '...'
            score = str(metadata.get('filter_score', 'N/A'))
            article_type = metadata.get('article_type', 'N/A')
            feed = article['feed_name']
            
            # 状態アイコン
            status_icons = []
            if article['is_favorite']:
                status_icons.append('⭐')
            if article['is_read']:
                status_icons.append('✓')
            else:
                status_icons.append('●')
            status = ''.join(status_icons)
            
            # スコアに応じて色を変更
            score_value = metadata.get('filter_score', 0)
            if score_value >= 8:
                score_style = "bold green"
            elif score_value >= 6:
                score_style = "yellow"
            else:
                score_style = "red"
            
            # タイトルのスタイル（既読は薄く表示）
            title_style = "dim" if article['is_read'] else "white"
            
            table.add_row(
                str(idx),
                status,
                feed,
                f"[{title_style}]{title}[/{title_style}]",
                f"[{score_style}]{score}[/{score_style}]",
                article_type
            )
        
        console.print(table)
    
    def display_article(self, article: Dict, index: int, total: int):
        """個別記事を表示"""
        metadata = article['metadata']
        
        # ヘッダー情報
        title = metadata.get('title', 'No Title')
        feed = article['feed_name']
        score = metadata.get('filter_score', 'N/A')
        article_type = metadata.get('article_type', 'N/A')
        url = metadata.get('url', '')
        author = metadata.get('author', 'Unknown')
        published = metadata.get('published', '')
        
        # 状態アイコン
        status_icons = []
        if article['is_favorite']:
            status_icons.append('⭐ お気に入り')
        if article['is_read']:
            status_icons.append('✓ 既読')
        else:
            status_icons.append('● 未読')
        status = ' | '.join(status_icons)
        
        # ヘッダーを表示（整形・色付け）
        console.print("━" * 80, style="cyan")
        console.print(f"📚 記事 {index}/{total}  |  {status}", style="bold cyan")
        console.print("━" * 80, style="cyan")
        console.print()
        console.print(f"Feed: [magenta]{feed}[/magenta]  |  Score: [green]{score}[/green]  |  Type: [blue]{article_type}[/blue]")
        console.print()
        console.print(f"Title: [bold white]{title}[/bold white]")
        console.print()
        console.print(f"URL: [blue underline]{url}[/blue underline]")
        console.print()
        console.print(f"Author: [dim]{author}[/dim]")
        console.print(f"Published: [dim]{published}[/dim]")
        console.print()
        console.print("━" * 80, style="cyan")
        console.print()
        
        # 本文を表示（通常表示）
        md = Markdown(article['content'])
        console.print(md)
    
    def display_article_with_pager(self, article: Dict, index: int, total: int):
        """ページャー付きで記事を表示"""
        metadata = article['metadata']
        
        # ヘッダー情報を準備
        title = metadata.get('title', 'No Title')
        feed = article['feed_name']
        score = metadata.get('filter_score', 'N/A')
        article_type = metadata.get('article_type', 'N/A')
        url = metadata.get('url', '')
        author = metadata.get('author', 'Unknown')
        published = metadata.get('published', '')
        
        # 状態アイコン
        status_icons = []
        if article['is_favorite']:
            status_icons.append('⭐ お気に入り')
        if article['is_read']:
            status_icons.append('✓ 既読')
        else:
            status_icons.append('● 未読')
        status = ' | '.join(status_icons)
        
        # ページャーで全体を表示
        with console.pager(styles=True):
            console.print("━" * 80, style="cyan")
            console.print(f"📚 記事 {index}/{total}  |  {status}", style="bold cyan")
            console.print("━" * 80, style="cyan")
            console.print()
            console.print(f"Feed: [magenta]{feed}[/magenta]  |  Score: [green]{score}[/green]  |  Type: [blue]{article_type}[/blue]")
            console.print()
            console.print(f"Title: [bold white]{title}[/bold white]")
            console.print()
            console.print()
            console.print(f"URL: [blue underline]{url}[/blue underline]")
            console.print()
            console.print(f"Author: [dim]{author}[/dim]")
            console.print(f"Published: [dim]{published}[/dim]")
            console.print()
            console.print("━" * 80, style="cyan")
            console.print()
            
            # 本文
            md = Markdown(article['content'])
            console.print(md)
    
    def interactive_mode(self, articles: List[Dict]):
        """インタラクティブモード"""
        if not articles:
            console.print("[yellow]表示する記事がありません[/yellow]")
            return
        
        current_index = 0
        
        while True:
            console.clear()
            current_article = articles[current_index]
            
            # 記事表示時に自動で既読マークをつける
            if not current_article['is_read']:
                self.state_manager.mark_as_read(current_article['article_id'])
                current_article['is_read'] = True
            
            self.display_article_with_pager(current_article, current_index + 1, len(articles))
            
            console.print("━" * 80)
            console.print("[cyan]操作キー:[/cyan]")
            console.print("  [N]ext | [P]rev | [L]ist | [Q]uit | [O]pen URL | [数字]で直接移動")
            console.print("  [R]ead/Unread | [F]avorite | [D]elete | [U]ndelete")
            console.print("━" * 80)
            
            choice = Prompt.ask("選択", default="n").lower()
            
            if choice == 'n' or choice == '':
                current_index = (current_index + 1) % len(articles)
            elif choice == 'p':
                current_index = (current_index - 1) % len(articles)
            elif choice == 'l':
                console.clear()
                self.display_article_list(articles)
                console.print()
                Prompt.ask("Enterで続行")
            elif choice == 'q':
                break
            elif choice == 'r':
                # 既読/未読トグル
                article_id = current_article['article_id']
                if current_article['is_read']:
                    self.state_manager.mark_as_unread(article_id)
                    current_article['is_read'] = False
                    console.print("[green]未読にマークしました[/green]")
                else:
                    self.state_manager.mark_as_read(article_id)
                    current_article['is_read'] = True
                    console.print("[green]既読にマークしました[/green]")
                Prompt.ask("Enterで続行")
            elif choice == 'f':
                # お気に入りトグル
                article_id = current_article['article_id']
                self.state_manager.toggle_favorite(article_id)
                current_article['is_favorite'] = self.state_manager.is_favorite(article_id)
                if current_article['is_favorite']:
                    console.print("[yellow]⭐ お気に入りに追加しました[/yellow]")
                else:
                    console.print("[yellow]お気に入りから削除しました[/yellow]")
                Prompt.ask("Enterで続行")
            elif choice == 'd':
                # 削除
                article_id = current_article['article_id']
                if Confirm.ask("この記事を削除しますか？"):
                    self.state_manager.mark_as_deleted(article_id)
                    current_article['is_deleted'] = True
                    console.print("[red]削除しました（ファイルは残っています）[/red]")
                    # 削除後、次の記事へ移動
                    articles = [a for a in articles if not a['is_deleted']]
                    if not articles:
                        console.print("[yellow]すべての記事を削除しました[/yellow]")
                        break
                    current_index = min(current_index, len(articles) - 1)
                    Prompt.ask("Enterで続行")
            elif choice == 'u':
                # 削除解除（削除済み記事を表示している場合）
                article_id = current_article['article_id']
                self.state_manager.undelete(article_id)
                current_article['is_deleted'] = False
                console.print("[green]削除を解除しました[/green]")
                Prompt.ask("Enterで続行")
            elif choice == 'o':
                # 元記事のURLを表示
                url = current_article['metadata'].get('url', '')
                if url:
                    console.print()
                    console.print("[bold cyan]📎 元記事URL:[/bold cyan]")
                    console.print(f"[blue underline]{url}[/blue underline]")
                    console.print()
                    console.print("[dim]※ Cmd+クリック（macOS）またはURLをコピーしてブラウザで開いてください[/dim]")
                else:
                    console.print("[red]URLが見つかりません[/red]")
                console.print()
                Prompt.ask("Enterで続行")
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(articles):
                    current_index = idx
                else:
                    console.print(f"[red]無効な番号です(1-{len(articles)})[/red]")
                    Prompt.ask("Enterキーで続行")


def main():
    parser = argparse.ArgumentParser(description='LLM RSS Curator - Article Viewer')
    parser.add_argument('--storage', default='/app/storage', help='ストレージパス')
    parser.add_argument('--feed', help='特定のフィードのみ表示 (aws, azure, zenn-llm)')
    parser.add_argument('--min-score', type=float, help='最小スコア（この値以上の記事のみ表示）')
    parser.add_argument('--type', choices=['news', 'tutorial'], help='記事タイプでフィルタ')
    parser.add_argument('--today', action='store_true', help='今日処理された記事のみ')
    parser.add_argument('--week', action='store_true', help='今週処理された記事のみ')
    parser.add_argument('--sort', choices=['score', 'date'], default='score', help='ソート順')
    parser.add_argument('--list-only', action='store_true', help='リスト表示のみ（インタラクティブモードに入らない）')
    parser.add_argument('--interactive', '-i', action='store_true', help='インタラクティブモード（デフォルト）')
    
    # 状態フィルタ
    parser.add_argument('--unread', action='store_true', help='未読記事のみ表示')
    parser.add_argument('--favorites', action='store_true', help='お気に入り記事のみ表示')
    parser.add_argument('--show-deleted', action='store_true', help='削除済み記事も表示')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    
    args = parser.parse_args()
    
    # 日付フィルタの設定
    since_date = None
    if args.today:
        since_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif args.week:
        since_date = datetime.now() - timedelta(days=7)
    
    # Article Viewerの初期化
    viewer = ArticleViewer(args.storage)
    
    # 統計情報のみ表示
    if args.stats:
        stats = viewer.state_manager.get_stats()
        console.print("\n[bold cyan]📊 記事管理統計[/bold cyan]\n")
        console.print(f"  既読記事: {stats['read_count']}件")
        console.print(f"  お気に入り: {stats['favorite_count']}件")
        console.print(f"  削除済み: {stats['deleted_count']}件")
        console.print(f"  アーカイブ: {stats['archived_count']}件\n")
        return
    
    # 記事を読み込み
    console.print("[cyan]記事を読み込み中...[/cyan]")
    articles = viewer.load_articles(
        feed=args.feed,
        min_score=args.min_score,
        article_type=args.type,
        since_date=since_date,
        show_deleted=args.show_deleted,
        unread_only=args.unread,
        favorites_only=args.favorites
    )
    
    # ソート
    if args.sort == 'score':
        articles.sort(key=lambda x: x['metadata'].get('filter_score', 0), reverse=True)
    else:
        articles.sort(key=lambda x: x['metadata'].get('published', ''), reverse=True)
    
    console.clear()
    
    # 表示
    if args.list_only:
        viewer.display_article_list(articles, sort_by=args.sort)
    else:
        # デフォルトはインタラクティブモード
        viewer.interactive_mode(articles)


if __name__ == '__main__':
    main()
