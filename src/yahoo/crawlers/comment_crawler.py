import os
from random import random
from typing import AsyncGenerator
import asyncio
from log_manager import log
from playwright.async_api import async_playwright, Page
from aiorwlock import RWLock
from consts import COMMENT_DIR, COMMENT_BATCH_SIZE
from .anchor_crawler import AnchorCrawler
from .page_to_do_plugins import (
    click_close_button,
    click_expand_buttons,
    click_more_replies_buttons,
    click_view_more_comments,
)


class CommentCrawler:
    def __init__(
        self,
        anchor_crawler: AnchorCrawler,  # AnchorCrawler 实例
        output_dir: str = COMMENT_DIR,
        concurrency: int = 5,
    ):
        """
        :param anchor_crawler: AnchorCrawler 的实例
        :param output_dir: 评论存储的文件夹
        :param concurrency: 最大并发任务数
        """
        self.anchor_crawler = anchor_crawler
        self.comment_selector = 'div[id="-post-rtjson-content"] p'
        self.output_dir = output_dir
        self.output_file = None
        self.concurrency = concurrency
        self.rw_lock = RWLock()

        # 确保存储目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    async def _scroll_page(self, page: Page) -> bool:
        """
        向下滚动页面加载更多内容
        :param page: Playwright 的 Page 对象
        :return: 如果加载了新内容返回 True，否则返回 False
        """
        try:
            prev_height = await page.evaluate("document.body.scrollHeight")
            log.info("滚动页面尝试获取更多内容")
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_load_state("networkidle")  # 等待加载完成
            await asyncio.sleep(random() * 2)  # 随机等待 0-2 秒
            curr_height = await page.evaluate("document.body.scrollHeight")
            return curr_height > prev_height  # 是否有新内容加载
        except Exception as e:
            log.error(f"页面滚动过程中发生错误：{e}")
            return False

    async def _extract_comments(self, page: Page) -> list[str]:
        """
        提取页面上的评论
        :param page: Playwright 的 Page 对象
        :return: 评论列表
        """
        try:
            elements = await page.query_selector_all(self.comment_selector)
            comments = [await element.inner_text() for element in elements]
            log.info(f"提取出 {len(comments)} 条评论")
            return comments
        except Exception as e:
            log.error(f"提取评论过程中发生错误：{e}")
            return []

    async def _is_new_content_loaded(
        self, comments: list[str], new_comments: list[str]
    ) -> list[str]:
        """
        检查是否加载了新评论并返回新增的评论
        :param comments: 已提取的评论列表
        :param new_comments: 当前页面的新评论
        :return: 新增的评论列表
        """
        added_comments = [c for c in new_comments if c not in comments]
        log.info(f"新加入了评论 {len(added_comments)} 条")
        return added_comments

    async def _fetch_comments(
        self, page: Page, url: str, page_to_do_plugins: list[callable] = None
    ) -> list[str]:
        """
        打开页面并提取评论内容，支持动态插件执行页面操作。
        :param page: Playwright 的 Page 对象
        :param url: 目标页面的 URL
        :param page_to_do_plugins: 动态注入的插件列表，每个插件是一个函数，接受 page 作为参数
        :return: 提取的评论列表
        """
        try:
            log.info(f"Opening URL for comments: {url}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")

            comments = []
            max_retries = 5
            retries = 0
            flush_idx = 0

            while retries < max_retries:
                try:
                    # 动态执行页面操作插件
                    if page_to_do_plugins:
                        for plugin in page_to_do_plugins:
                            try:
                                await plugin(page)  # 调用插件函数
                                log.info(f"执行插件 {plugin.__name__} 成功")
                            except Exception as e:
                                log.warning(f"执行插件 {plugin.__name__} 时出错：{e}")

                    # 获取当前页面的评论
                    new_comments = await self._extract_comments(page)

                    # 添加新评论
                    added_comments = await self._is_new_content_loaded(
                        comments, new_comments
                    )
                    if added_comments:
                        comments.extend(added_comments)

                        # 每 50 条评论保存一次
                        if comments and len(comments) - flush_idx >= COMMENT_BATCH_SIZE:
                            await self._save_comments(
                                self.output_file, comments[flush_idx:]
                            )
                            flush_idx = len(comments)

                    # 滚动页面加载更多内容
                    scrolled = await self._scroll_page(page)

                    # 如果没有新内容加载或展开按钮点击效果，增加重试计数
                    if not scrolled and not added_comments:
                        retries += 1
                        log.warning(
                            f"没有新的评论被加载，重试：{retries}/{max_retries}"
                        )
                    else:
                        retries = 0  # 重置重试计数

                except Exception as e:
                    log.error(f"获取评论过程中出现意外：{e}")
                    break

            log.info(f"获取了 {len(comments)} 条评论自 {url}")
            return comments

        except Exception as e:
            log.error(f"从 {url} 获取评论发生错误：{e}")
            return []

    async def _save_comments(self, file_name: str, comments: list[str]):
        """
        将评论追加保存到文件中
        :param file_name: 评论文件的路径
        :param comments: 评论内容列表
        """
        async with self.rw_lock.writer_lock:
            try:
                with open(file_name, "a", encoding="utf-8") as f:
                    for comment in comments:
                        f.write(comment + "\n")
                log.info(f"追加 {len(comments)} 条评论到 {file_name}")
            except Exception as e:
                log.error(f"保存评论至 {file_name} 时发生错误: {e}")

    async def _wait_for_links(
        self,
        all_links: AsyncGenerator[tuple[str, str], None],
        timeout: int = 60,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        等待链接生成，若超过超时时间则停止等待。
        :param all_links: 所有链接的异步生成器
        :param timeout: 最大闲置等待时间（秒）
        :return: 链接的异步生成器
        """
        start_time = asyncio.get_event_loop().time()

        async for link in all_links:
            yield link
            start_time = asyncio.get_event_loop().time()  # 重置闲置计时

            # 避免阻塞事件循环
            await asyncio.sleep(0)

        # 如果超时，退出
        while asyncio.get_event_loop().time() - start_time < timeout:
            await asyncio.sleep(1)  # 间隔检查是否超时

        log.warning("超时未获取新链接，停止爬取任务。")

    async def process_links(self, instance_id: int, total_instances: int):
        """
        处理指定的链接生成器，爬取评论
        :param instance_id: 当前实例的 ID
        :param total_instances: 总实例数
        """
        all_links = self.anchor_crawler.read_persisted_links()  # 获取持久化的链接
        filtered_links = self.get_link_generator(
            all_links, instance_id, total_instances
        )
        links = self._wait_for_links(filtered_links, timeout=60)  # 设置超时时间为 60 秒

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            async for hash_key, link in links:
                # 评论文件路径
                file_name = os.path.join(self.output_dir, f"{hash_key}.txt")
                self.output_file = file_name

                # 如果文件已存在，跳过（避免重复爬取）
                if os.path.exists(file_name):
                    log.info(f"文件 {file_name} 已经存在，跳过")
                    continue

                # 爬取评论
                comments = await self._fetch_comments(
                    page,
                    link,
                    page_to_do_plugins=[
                        click_view_more_comments,
                        click_close_button,
                        click_expand_buttons,
                        click_more_replies_buttons,
                    ],
                )

                # 保存评论
                await self._save_comments(file_name, comments)

            await browser.close()

    async def get_link_generator(
        self,
        all_links: AsyncGenerator[tuple[str, str], None],
        instance_id: int,
        total_instances: int,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        根据实例 ID 和总实例数，筛选出当前实例负责的链接（异步生成器）
        :param all_links: 所有链接的异步生成器
        :param instance_id: 当前实例的 ID
        :param total_instances: 总实例数
        :return: 当前实例负责的链接异步生成器
        """
        i = 0
        async for hash_key, link in all_links:
            if i % total_instances == instance_id:
                yield hash_key, link
            i += 1
            await asyncio.sleep(0)  # 避免阻塞事件循环

    @classmethod
    async def run_all_instances(
        cls, total_instances: int, anchor_crawler: AnchorCrawler
    ):
        """
        初始化并运行多个 CommentCrawler 实例，完成并发爬取评论的任务
        :param total_instances: 并发实例总数
        :param anchor_crawler: AnchorCrawler 的实例
        """
        # 初始化 CommentCrawler 实例
        comment_crawlers = [
            cls(anchor_crawler=anchor_crawler) for _ in range(total_instances)
        ]

        # 创建任务
        tasks = [
            crawler.process_links(instance_id=i, total_instances=total_instances)
            for i, crawler in enumerate(comment_crawlers)
        ]

        # 并发运行所有实例
        await asyncio.gather(*tasks)
