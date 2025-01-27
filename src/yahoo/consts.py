from pathlib import Path

# 根目录
ROOT_DIR = Path("F:/proj/temp/yahoo")
# 日志文件路径
LOG_FILE = ROOT_DIR / "logs" / "app.log"
# 评论文件目录
COMMENT_DIR = ROOT_DIR / "comments"
# 历史链接记录文件路径
ANCHOR_FILE = ROOT_DIR / "anchor" / "anchor_history.txt"
# 分析目录
ANALYZE_DIR = ROOT_DIR / "analyze"
# 停用词文件路径
STOP_WORDS_FILE = ANALYZE_DIR / "stop_words_english.txt"
# 分析结果路径
OUTPUT_CSV = ANALYZE_DIR / "word_frequency.csv"

# 批量写入阈值
ANCHOR_BATCH_SIZE = 200
# 评论批量写入阈值
COMMENT_BATCH_SIZE = 50

# 爬取目标链接
TARGET_URL = "https://www.reddit.com/r/yahoo/"
MAX_LINKS = 10000  # 设置爬取的最大链接数量

# 内容分隔符号
KEY_VALUE_SEPARATOR = "\u241F"  # Unit Separator (ASCII 31)
ITEM_SEPARATOR = "\u241E"  # Record Separator (ASCII 30)

# 评论爬取的并发数
TOTAL_INSTANCE = 10
