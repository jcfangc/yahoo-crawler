import asyncio
from enum import Enum
from crawlers.anchor_crawler import AnchorCrawler
from crawlers.comment_crawler import CommentCrawler
from analyze.word_frequency_analyst import WordFrequencyAnalyzer
from consts import TOTAL_INSTANCE


class MainCommand(Enum):
    ANCHOR = "anchor"
    COMMENT = "comment"
    ANALYZE = "analyze"
    BOTH = "both"


# 通过修改这里的值来改变行为
MAIN_COMMAND = MainCommand.BOTH


async def main() -> None:
    if MAIN_COMMAND in [MainCommand.ANCHOR, MainCommand.BOTH, MainCommand.COMMENT]:
        anchor_crawler: AnchorCrawler = AnchorCrawler()

    # 如果要对爬取的评论信息进行分析
    if MAIN_COMMAND == MainCommand.ANALYZE:
        await WordFrequencyAnalyzer().analyze()

    # 如果要爬取 yahoo 的讨论链接
    elif MAIN_COMMAND == MainCommand.ANCHOR:
        anchor_task: asyncio.Future = anchor_crawler.start_crawling()
        await anchor_task

    # 如果要跟据已有的讨论链接爬取评论
    elif MAIN_COMMAND == MainCommand.COMMENT:
        comment_task: asyncio.Future = CommentCrawler.run_all_instances(
            total_instances=TOTAL_INSTANCE, anchor_crawler=anchor_crawler
        )
        await comment_task

    # 如果要同时进行链接的爬取和对应评论的爬取，最好已经有一些链接存在，否则评论爬取可能会卡住
    elif MAIN_COMMAND == MainCommand.BOTH:
        comment_task: asyncio.Future = CommentCrawler.run_all_instances(
            total_instances=TOTAL_INSTANCE, anchor_crawler=anchor_crawler
        )
        anchor_task: asyncio.Future = anchor_crawler.start_crawling()
        await asyncio.gather(anchor_task, comment_task)


if __name__ == "__main__":
    asyncio.run(main())
