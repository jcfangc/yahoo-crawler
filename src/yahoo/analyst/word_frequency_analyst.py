import re
import csv
import asyncio
from pathlib import Path
from collections import Counter
from aiofiles import open as aio_open
from consts import STOP_WORDS_FILE, COMMENT_DIR, OUTPUT_CSV


class WordFrequencyAnalyzer:
    def __init__(
        self,
        stopwords_file: Path = STOP_WORDS_FILE,
        comment_dir: Path = COMMENT_DIR,
        output_csv: Path = OUTPUT_CSV,
        num_partitions: int = 4,
    ):
        """
        初始化词频分析器
        :param stopwords_file: 停用词文件路径
        :param comment_dir: 评论文件目录
        :param output_csv: 输出的 CSV 文件路径
        :param num_partitions: 分区数量，用于分布式统计
        """
        self.stopwords_file = stopwords_file
        self.comment_dir = comment_dir
        self.output_csv = output_csv
        self.num_partitions = num_partitions
        self.stopwords = set()

    async def load_stopwords(self):
        """
        异步加载停用词表
        """
        try:
            async with aio_open(self.stopwords_file, "r", encoding="utf-8") as f:
                self.stopwords = {
                    word.strip() for word in await f.readlines() if word.strip()
                }
        except Exception as e:
            print(f"Error loading stopwords: {e}")
            self.stopwords = set()

    def preprocess_text(self, text: str) -> list[str]:
        """
        文本预处理，去除停用词
        """
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\d+", " ", text)
        words = text.split()
        words = [word for word in words if word not in self.stopwords]
        return words

    async def process_file(self, file_path: Path) -> Counter:
        """
        异步处理单个文件，统计词频
        """
        try:
            async with aio_open(file_path, "r", encoding="utf-8") as f:
                text = await f.read()
                words = self.preprocess_text(text)
                return Counter(words)
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return Counter()

    async def analyze(self):
        """
        主流程：加载停用词表、处理文件、汇总结果并保存到 CSV
        """
        # 加载停用词表
        await self.load_stopwords()

        # 初始化分区计数器
        partition_counters = {i: Counter() for i in range(self.num_partitions)}

        # 异步处理所有文件
        tasks = [
            self.handle_file_with_partitioning(file_path, partition_counters)
            for file_path in self.comment_dir.iterdir()
            if file_path.is_file() and file_path.suffix == ".txt"
        ]
        await asyncio.gather(*tasks)

        # 汇总所有分区结果
        total_counter = self.merge_partitions(partition_counters)

        # 保存结果到 CSV 文件
        self.save_to_csv(total_counter)

    async def handle_file_with_partitioning(
        self, file_path: Path, partition_counters: dict[int, Counter]
    ):
        """
        异步处理单个文件并将结果分配到相应的分区
        """
        file_counter = await self.process_file(file_path)
        partition_index = int(file_path.name[0], 16) % self.num_partitions
        partition_counters[partition_index].update(file_counter)

    @staticmethod
    def merge_partitions(partition_counters: dict[int, Counter]) -> Counter:
        """
        合并所有分区的计数器
        """
        total_counter = Counter()
        for counter in partition_counters.values():
            total_counter.update(counter)
        return total_counter

    def save_to_csv(self, counter: Counter):
        """
        将计数器内容保存到 CSV 文件
        """
        try:
            with self.output_csv.open("w", encoding="utf-8", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["word", "frequency"])  # 写入表头
                for word, freq in counter.items():
                    writer.writerow([word, freq])
            print(f"词频分析结果已保存到 {self.output_csv}")
        except Exception as e:
            print(f"保存到 CSV 文件时发生错误: {e}")
