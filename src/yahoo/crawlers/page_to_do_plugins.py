import asyncio
import random
from log_manager import log
from playwright.async_api import Page, ElementHandle


async def _safe_click(button: ElementHandle, retries=3):
    for attempt in range(retries):
        try:
            await button.click(timeout=int(500 * random()))
            log.info("按钮点击成功")
            return
        except Exception as e:
            log.warning(f"点击按钮失败，重试 {attempt + 1}/{retries} 次：{e}")
            await asyncio.sleep(1)


async def _click_buttons_once(
    page: Page, button_selector: str, description: str
) -> bool:
    """
    通用方法：点击页面上所有符合条件的按钮（只执行一次）。
    :param page: Playwright 的 Page 对象
    :param button_selector: 按钮的 CSS 选择器
    :param description: 按钮描述（日志用）
    :return: 如果至少点击了一个按钮返回 True，否则返回 False
    """
    try:
        # 查询所有符合条件的按钮
        buttons = await page.query_selector_all(button_selector)

        if not buttons:
            log.info(f"没有找到{description}")
            return False

        log.info(f"发现 {len(buttons)} 个{description}，开始逐一点击")
        total_clicks = 0

        for button in buttons:
            try:
                # 将按钮滚动到视口范围内
                await button.scroll_into_view_if_needed()
                log.debug(f"已滚动至 {description} 按钮可见位置")
                await _safe_click(button)
                await page.wait_for_load_state("networkidle")  # 等待页面加载完成
                await asyncio.sleep(random() * 2)  # 随机等待 0-2 秒
                await page.mouse.move(0, 0)  # 移动鼠标到页面左上角，避免悬浮干扰
                log.debug("鼠标已移到页面左上角以避免悬浮干扰")
                total_clicks += 1
            except Exception as e:
                log.warning(f"点击{description}时出现问题：{e}")

        log.info(f"完成 {description} 的点击，总共点击了 {total_clicks} 次")
        return total_clicks > 0

    except Exception as e:
        log.error(f"查找或点击{description}时出错：{e}")
        return False


async def click_close_button(page: Page) -> bool:
    """
    检查并点击页面上的关闭按钮
    :param page: Playwright 的 Page 对象
    :return: 如果找到了关闭按钮并成功点击，返回 True；否则返回 False
    """
    return await _click_buttons_once(
        page=page,
        button_selector='button[aria-label="Close"]:has(svg[icon-name="close-outline"])',
        description="关闭按钮",
    )


async def click_expand_buttons(page: Page) -> bool:
    """
    点击页面上所有的“展开评论”按钮，直到没有新按钮。
    :param page: Playwright 的 Page 对象
    :return: 如果至少点击了一个按钮返回 True，否则返回 False
    """
    return await _click_buttons_once(
        page,
        button_selector='button:has(svg[icon-name="join-outline"])',
        description="展开评论按钮",
    )


async def click_more_replies_buttons(page: Page) -> bool:
    """
    点击页面上的“x more replies”按钮，直到没有新按钮。
    :param page: Playwright 的 Page 对象
    :return: 如果至少点击了一个按钮返回 True，否则返回 False
    """
    return await _click_buttons_once(
        page,
        button_selector='button:has-text("more replies")',
        description="更多回复按钮",
    )


async def click_view_more_comments(page: Page) -> bool:
    """
    点击 "View more comments" 按钮（如果存在）
    :param page: Playwright 的 Page 对象
    :return: 如果点击了按钮返回 True，否则返回 False
    """
    return await _click_buttons_once(
        page=page,
        button_selector='button:has-text("View more comments")',
        description="View more comments 按钮",
    )
