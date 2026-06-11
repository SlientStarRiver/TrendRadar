"""
从 SQLite 输出生成 Obsidian 兼容的 Markdown 文件。

用法: python scripts/generate_obsidian_md.py [--date YYYY-MM-DD] [--output-dir output] [--vault-dir obsidian_vault]
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def read_news_db(db_path: Path) -> list[dict]:
    """读取 news SQLite 数据库，返回最新抓取的新闻列表。"""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 获取最新一次抓取时间
    row = conn.execute(
        "SELECT crawl_time FROM crawl_records ORDER BY crawl_time DESC LIMIT 1"
    ).fetchone()
    if not row:
        conn.close()
        return []

    latest_time = row["crawl_time"]

    # 通过 rank_history 获取最新抓取的 news_item_id 和排名
    rows = conn.execute(
        """
        SELECT ni.title, ni.platform_id, p.name AS platform_name,
               ni.rank, ni.url, ni.mobile_url, ni.crawl_count,
               rh.rank AS latest_rank
        FROM rank_history rh
        JOIN news_items ni ON ni.id = rh.news_item_id
        LEFT JOIN platforms p ON p.id = ni.platform_id
        WHERE rh.crawl_time = ?
        ORDER BY rh.rank ASC
        """,
        (latest_time,),
    ).fetchall()

    conn.close()

    items = []
    for r in rows:
        items.append(
            {
                "title": r["title"],
                "platform_id": r["platform_id"],
                "platform_name": r["platform_name"] or r["platform_id"],
                "rank": r["latest_rank"] or r["rank"],
                "url": r["mobile_url"] or r["url"] or "",
                "crawl_count": r["crawl_count"],
            }
        )
    return items


def read_rss_db(db_path: Path) -> list[dict]:
    """读取 RSS SQLite 数据库。"""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT ri.title, ri.feed_id, rf.name AS feed_name,
               ri.url, ri.published_at, ri.summary
        FROM rss_items ri
        LEFT JOIN rss_feeds rf ON rf.id = ri.feed_id
        ORDER BY ri.published_at DESC
        """
    ).fetchall()

    conn.close()

    items = []
    for r in rows:
        items.append(
            {
                "title": r["title"],
                "feed_id": r["feed_id"],
                "feed_name": r["feed_name"] or r["feed_id"],
                "url": r["url"] or "",
                "published_at": r["published_at"] or "",
                "summary": r["summary"] or "",
            }
        )
    return items


def generate_daily_markdown(date: str, news_items: list[dict], rss_items: list[dict]) -> str:
    """生成每日 Markdown 笔记。"""
    lines = [
        "---",
        f"date: {date}",
        "type: daily-trend",
        "tags: [trendradar, daily]",
        "---",
        "",
        f"# {date} AI 热点速报",
        "",
    ]

    # 按平台分组
    by_platform: dict[str, list[dict]] = {}
    for item in news_items:
        src = item["platform_name"]
        by_platform.setdefault(src, []).append(item)

    if by_platform:
        lines.append("## 热榜新闻")
        lines.append("")
        for platform, items in by_platform.items():
            lines.append(f"### {platform}")
            lines.append("")
            for i, item in enumerate(items[:15], 1):
                title = item["title"]
                url = item["url"]
                rank = item["rank"]
                count = item["crawl_count"]
                rank_str = f" `#{rank}`" if rank and rank <= 10 else ""
                count_str = f" ({count}次)" if count and count > 1 else ""
                if url:
                    lines.append(f"{i}. [{title}]({url}){rank_str}{count_str}")
                else:
                    lines.append(f"{i}. {title}{rank_str}{count_str}")
            lines.append("")

    if rss_items:
        lines.append("## RSS 订阅")
        lines.append("")
        by_feed: dict[str, list[dict]] = {}
        for item in rss_items:
            feed = item["feed_name"]
            by_feed.setdefault(feed, []).append(item)

        for feed, items in by_feed.items():
            lines.append(f"### {feed}")
            lines.append("")
            for i, item in enumerate(items[:10], 1):
                title = item["title"]
                url = item["url"]
                pub = item["published_at"]
                pub_str = f" `{pub}`" if pub else ""
                if url:
                    lines.append(f"{i}. [{title}]({url}){pub_str}")
                else:
                    lines.append(f"{i}. {title}{pub_str}")
            lines.append("")

    lines.extend([
        "---",
        "*由 TrendRadar 自动生成*",
        "",
    ])

    return "\n".join(lines)


def generate_source_markdown(date: str, source: str, items: list[dict]) -> str:
    """为单个来源生成 Markdown 笔记。"""
    lines = [
        "---",
        f"date: {date}",
        f"source: {source}",
        "type: source-trend",
        "tags: [trendradar, source]",
        "---",
        "",
        f"# {source} — {date}",
        "",
    ]

    for i, item in enumerate(items[:20], 1):
        title = item["title"]
        url = item["url"]
        rank = item.get("rank", "")
        rank_str = f" `#{rank}`" if rank and rank <= 10 else ""
        if url:
            lines.append(f"{i}. [{title}]({url}){rank_str}")
        else:
            lines.append(f"{i}. {title}{rank_str}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成 Obsidian Markdown 文件")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--output-dir", default="output", help="SQLite 输出目录")
    parser.add_argument("--vault-dir", default="obsidian_vault", help="Obsidian vault 输出目录")
    args = parser.parse_args()

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(args.output_dir)
    vault_dir = Path(args.vault_dir)

    # 创建目录
    daily_dir = vault_dir / "Daily"
    source_dir = vault_dir / "AI"
    daily_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    # 读取数据
    news_db = output_dir / "news" / f"{date}.db"
    rss_db = output_dir / "rss" / f"{date}.db"

    news_items = read_news_db(news_db)
    rss_items = read_rss_db(rss_db)

    if not news_items and not rss_items:
        print(f"[Obsidian] {date} 无数据，跳过")
        return

    # 生成每日汇总
    daily_md = generate_daily_markdown(date, news_items, rss_items)
    daily_file = daily_dir / f"{date}.md"
    daily_file.write_text(daily_md, encoding="utf-8")
    print(f"[Obsidian] 每日笔记: {daily_file}")

    # 按来源生成分类笔记
    by_platform: dict[str, list[dict]] = {}
    for item in news_items:
        src = item["platform_name"]
        by_platform.setdefault(src, []).append(item)

    for source, items in by_platform.items():
        safe_name = source.replace("/", "_").replace("\\", "_").replace(" ", "_")
        md = generate_source_markdown(date, source, items)
        src_file = source_dir / f"{safe_name}_{date}.md"
        src_file.write_text(md, encoding="utf-8")

    print(f"[Obsidian] 已生成 {len(by_platform)} 个来源笔记到 {source_dir}")


if __name__ == "__main__":
    main()
