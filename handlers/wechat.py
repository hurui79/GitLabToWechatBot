"""企业微信机器人消息发送"""
import requests
import logging

logger = logging.getLogger(__name__)


def send_markdown(wechat_url, content):
    """发送 markdown 消息到企业微信机器人

    Args:
        wechat_url: 企业微信机器人 webhook URL
        content: markdown 内容

    Returns:
        (success: bool, message: str)
    """
    body = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    try:
        resp = requests.post(
            wechat_url,
            json=body,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        result = resp.json()
        if result.get('errcode') == 0:
            return True, '发送成功'
        else:
            msg = f"企业微信返回错误: {result.get('errmsg', '未知错误')}"
            logger.warning(msg)
            return False, msg
    except requests.RequestException as e:
        msg = f"请求企业微信失败: {e}"
        logger.error(msg)
        return False, msg


def send_test(wechat_url):
    """发送测试消息"""
    content = (
        "**[测试消息] GitLab → 企业微信**\n"
        "> 这是一条测试消息\n"
        "> 如果你看到这条消息，说明 webhook 配置正确 ✅"
    )
    return send_markdown(wechat_url, content)
