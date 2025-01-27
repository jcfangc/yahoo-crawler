

# Yahoo Discussion Scraper  
**雅虎讨论爬虫**

This is a toy project designed to scrape discussions related to Yahoo from Reddit, extract comments, and perform word frequency analysis on the collected data. The project is modular and uses Python for implementation, with asynchronous crawling powered by Playwright.  
这是一个用于从 Reddit 上爬取与雅虎相关讨论的玩具项目，可以提取评论并对收集到的数据进行词频分析。项目采用模块化设计，并使用 Python 实现，异步爬取基于 Playwright。

---

## Project Structure  
**项目结构**

```
src/
├── analyze/
│   ├── word_frequency_analyst.py       # Handles word frequency analysis  
│       # 处理词频分析的模块
├── crawlers/
│   ├── anchor_crawler.py               # Crawls and stores discussion links  
│       # 爬取并存储讨论链接
│   ├── comment_crawler.py              # Crawls comments from discussion links  
│       # 从讨论链接中爬取评论
│   ├── page_to_do_plugins.py           # Plugins for page interaction during crawling  
│       # 页面交互插件，用于爬取过程
├── consts.py                           # Contains global constants and settings  
│       # 定义全局常量和配置
├── log_manager.py                      # Logging utilities  
│       # 日志管理工具
├── main.py                             # Entry point for the project  
│       # 项目入口
```

---

## Features  
**功能特点**

1. **Link Crawling**:  
   - `anchor_crawler.py` fetches discussion links from Reddit and stores them with unique hash keys.  
   - `anchor_crawler.py` 用于从 Reddit 获取讨论链接，并使用唯一哈希键存储。

2. **Comment Crawling**:  
   - `comment_crawler.py` uses Playwright to navigate through pages, handle interactions, and extract comments.  
   - `comment_crawler.py` 使用 Playwright 处理页面交互并提取评论。

3. **Plugin Support**:  
   - Modular plugins in `page_to_do_plugins.py` provide customizable page interaction (e.g., expanding comments, closing modals).  
   - `page_to_do_plugins.py` 提供模块化插件，用于自定义页面交互（例如展开评论或关闭弹窗）。

4. **Word Frequency Analysis**:  
   - `word_frequency_analyst.py` analyzes the collected comments to compute word frequencies and outputs the results in CSV format.  
   - `word_frequency_analyst.py` 分析收集到的评论，计算词频并将结果输出为 CSV 文件。

5. **Logging**:  
   - Centralized logging using `log_manager.py` for better debugging and monitoring.  
   - 使用 `log_manager.py` 进行集中式日志记录，便于调试和监控。

---

## Usage  
**使用方法**

### Prerequisites  
**环境准备**

- Python 3.10 or above  
  - Python 3.10 或以上版本  
- Playwright installed with browser dependencies  
  - 已安装 Playwright 及其浏览器依赖  
- Dependencies installed via Poetry  
  - 使用 Poetry 安装依赖  

### Installation  
**安装步骤**

1. Clone the repository:  
   **克隆项目代码：**  
   ```bash
   git clone <repository-url>
   cd yahoo
   ```

2. Install dependencies:  
   **安装依赖：**  
   ```bash
   poetry install
   ```

3. Install Playwright browsers:  
   **安装 Playwright 浏览器：**  
   ```bash
   playwright install
   ```

### Running the Project  
**运行项目**

You can control the functionality by modifying `MAIN_COMMAND` in `main.py`:  
可以通过修改 `main.py` 中的 `MAIN_COMMAND` 来控制项目功能：

- **`MainCommand.ANCHOR`**: Crawl discussion links only.  
  **爬取讨论链接**  
- **`MainCommand.COMMENT`**: Crawl comments from the links.  
  **爬取评论**  
- **`MainCommand.ANALYZE`**: Perform word frequency analysis.  
  **进行词频分析**  
- **`MainCommand.BOTH`**: Crawl links and comments simultaneously.  
  **同时爬取链接和评论**  

Run the project:  
运行项目：  
```bash
python -m src.yahoo.main
```

### Outputs  
**输出结果**

- **Links**: Saved in `anchor/anchor_history.txt`.  
  **讨论链接**：存储在 `anchor/anchor_history.txt`  
- **Comments**: Saved in `comments/` with filenames based on hash keys.  
  **评论**：存储在 `comments/` 文件夹中，文件名基于哈希键命名。  
- **Analysis**: Word frequency data saved in `analyze/word_frequency.csv`.  
  **分析结果**：词频数据存储在 `analyze/word_frequency.csv`  

---

## Key Notes  
**注意事项**

- **Extensibility**: Use `page_to_do_plugins.py` to add or modify interaction behaviors during crawling.  
  **可扩展性**：通过 `page_to_do_plugins.py` 添加或修改爬取过程中的页面交互行为。  
- **Modularity**: Clear separation of concerns for easier maintenance and debugging.  
  **模块化**：清晰的模块分离便于维护和调试。