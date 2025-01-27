from loguru import logger
from consts import LOG_FILE

# 移除默认的控制台输出
logger.remove()

# 添加日志记录到文件
logger.add(
    LOG_FILE,
    rotation="10 MB",  # 文件达到 10 MB 时自动创建新文件
    retention="1 days",  # 保留日志文件 1 天
    compression="zip",  # 压缩旧日志文件
    enqueue=True,  # 支持多线程/异步写入
    backtrace=True,  # 捕获完整回溯信息
    diagnose=True,  # 输出变量详细信息
    level="DEBUG",  # 设置日志记录等级
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file.path}:{line}\n{message}",  # 将 message 换行显示
)

# 示例日志记录器导出
log = logger
