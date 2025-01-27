import hashlib
import asyncio
import os
from typing import AsyncGenerator
import aiofiles
import random
from log_manager import log
from playwright.async_api import async_playwright, Page
from consts import (
    TARGET_URL,
    MAX_LINKS,
    ANCHOR_BATCH_SIZE,
    ANCHOR_FILE,
    ITEM_SEPARATOR,
    COMMENT_DIR,
    KEY_VALUE_SEPARATOR,
)
from aiorwlock import RWLock
from urllib.parse import urljoin
from pathlib import Path


class AnchorCrawler:
    def __init__(
        self,
        target_url: str = TARGET_URL,
        max_links: int = MAX_LINKS,
        output_file: str = ANCHOR_FILE,
        batch_size: int = ANCHOR_BATCH_SIZE,
        comment_dir: Path = COMMENT_DIR,
        scroll_retries: int = 5,
    ):
        """
        :param target_url: 爬取的目标 URL
        :param max_links: 最大爬取的链接数
        :param output_file: 输出文件路径
        :param batch_size: 每批次保存的链接数
        :param comment_dir: 评论爬取结果的持久化文件
        :param scroll_retries: 页面滚动尝试次数
        """
        self.target_url = target_url
        self.max_links = max_links
        self.batch_size = batch_size
        self.output_file = output_file
        self.scroll_retries = scroll_retries
        self.comment_dir = comment_dir

        self.target_selector = (
            'shreddit-feed a[slot="full-post-link"][href*="/r/yahoo/comments/"]'
        )
        self.links = {}
        self.last_written_key = None
        self.key_value_separator = KEY_VALUE_SEPARATOR  # Unit Separator (ASCII 31)
        self.item_separator = ITEM_SEPARATOR  # Record Separator (ASCII 30)

        # 初始化读写锁
        self.rw_lock = RWLock()

        # 确保存储目录存在
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # 恢复最后写入的状态
        self._load_last_written_key()

    def _load_last_written_key(self):
        """
        从输出文件中恢复最后写入的键（哈希值）
        """
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        # 提取最后一行，去掉前缀的 ITEM_SEPARATOR
                        last_line = lines[-1].strip()
                        if last_line.startswith(self.item_separator):
                            last_line = last_line[len(self.item_separator) :]
                        # 获取哈希值部分
                        if self.key_value_separator in last_line:
                            self.last_written_key = last_line.split(
                                self.key_value_separator, 1
                            )[0]
                            log.info(f"最后的写入键：{self.last_written_key}")
        except Exception as e:
            log.error(f"载入最后写入键时发生错误：{e}")

    async def _filtered_link_generator(
        self,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        从 last_written_key 开始，异步生成未写入的键值对
        """
        start_yielding = (
            self.last_written_key is None
        )  # 如果未定义 last_written_key，从头开始
        for key, value in self.links.items():
            if not start_yielding:
                if key == self.last_written_key:
                    start_yielding = True  # 找到起点，开始生成
                continue
            yield key, value
            await asyncio.sleep(0)  # 让出事件循环，避免阻塞

    async def _save_links_incrementally(self):
        """
        增量保存链接到文件
        """
        async with self.rw_lock.writer_lock:
            try:
                with open(self.output_file, "a", encoding="utf-8") as f:
                    async for key, value in self._filtered_link_generator():
                        f.write(
                            f"{self.item_separator}{key}{self.key_value_separator}{value}\n"
                        )
                        self.last_written_key = key  # 更新最后写入的键
                log.info(f"追加链接到 {self.output_file}")
            except Exception as e:
                log.error(f"保存链接时发生错误：{e}")

    async def _hash_link(self, link: str) -> str:
        """
        使用 MD5 计算链接的哈希值
        """
        return hashlib.md5(link.encode("utf-8")).hexdigest()

    async def read_persisted_links(self) -> AsyncGenerator[tuple[str, str], None]:
        """
        异步逐行读取持久化的链接记录，并与 COMMENT_DIR 进行比对，跳过已爬取的链接。

        :yield: (hash_key, link) 键值对
        """
        try:
            # 获取已经爬取过的哈希文件名集合
            completed_hashes = {
                file.stem
                for file in self.comment_dir.iterdir()
                if file.suffix == ".txt"
            }
            log.info(f"已爬取的文件数量：{len(completed_hashes)}")

            if os.path.exists(self.output_file):
                async with aiofiles.open(self.output_file, "r", encoding="utf-8") as f:
                    async for line in f:
                        line = line.strip()
                        if line.startswith(self.item_separator):
                            line = line[len(self.item_separator) :]  # 去掉开头的分隔符
                        if self.key_value_separator in line:
                            # 分割出键值对
                            key, value = line.split(self.key_value_separator, 1)
                            if key in completed_hashes:
                                log.info(f"跳过已爬取的链接：{value}")
                                continue
                            yield key, value
        except Exception as e:
            log.error(f"读取持久化链接文件时发生错误：{e}")

    async def scroll_and_collect_links(self, page: Page):
        """
        不断滚动页面并收集目标链接
        """
        prev_height = 0
        retries = 0
        max_retries = self.scroll_retries

        while len(self.links) < self.max_links:
            try:
                # 滚动到页面底部
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(random.random() * 3)

                # 获取新链接
                elements = await page.query_selector_all(self.target_selector)
                for element in elements:
                    link = await element.get_attribute("href")
                    if link:
                        # 补全相对路径为完整路径
                        full_link = urljoin(self.target_url, link)
                        hashed = await self._hash_link(full_link)
                        if hashed not in self.links:
                            self.links[hashed] = full_link

                # 增量保存进度
                if len(self.links) % self.batch_size == 0:
                    await self._save_links_incrementally()

                # 检查是否继续滚动
                curr_height = await page.evaluate("document.body.scrollHeight")
                if curr_height == prev_height:
                    retries += 1
                    if retries >= max_retries:
                        log.warning("滚动尝试次数过多，退出滚动")
                        break
                else:
                    retries = 0
                prev_height = curr_height

            except Exception as e:
                log.error(f"滚动获取链接过程中发生意外：{e}")
                break

    async def start_crawling(self):
        """
        启动爬取任务
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                log.info(f"正在前往：{self.target_url}")
                await page.goto(self.target_url, timeout=60000)
                await self.scroll_and_collect_links(page)
            except Exception as e:
                log.error(f"爬取过程中发生错误：{e}")
            finally:
                # 保存剩余的链接
                await self._save_links_incrementally()
                await browser.close()
