"""GitLab webhook 事件解析与消息格式化"""
import logging

logger = logging.getLogger(__name__)

# 事件类型 → 中文标题
EVENT_TITLES = {
    'push': '代码推送',
    'tag_push': '标签推送',
    'merge_request': '合并请求',
    'note': '评论',
    'pipeline': '流水线',
    'wiki': 'Wiki',
    'build': '构建',
}


def parse_event(data):
    """解析 GitLab webhook 数据，返回 (event_type, project_name)

    Args:
        data: GitLab webhook JSON 数据

    Returns:
        (event_type: str, project_name: str)
    """
    event_type = data.get('object_kind', 'unknown')
    project = data.get('project', data.get('repository', {}))
    project_name = project.get('name', project.get('path_with_namespace', '未知项目'))
    return event_type, project_name


def format_message(data):
    """将 GitLab webhook 数据格式化为企业微信 markdown 消息

    Args:
        data: GitLab webhook JSON 数据

    Returns:
        markdown 格式字符串
    """
    event_type = data.get('object_kind', 'unknown')
    handler = _handlers.get(event_type, _format_unknown)
    return handler(data)


# ---------- 各事件格式化器 ----------

def _format_push(data):
    user = data.get('user_name', '未知用户')
    ref = data.get('ref', '').replace('refs/heads/', '')
    project = data.get('project', data.get('repository', {}))
    project_name = project.get('name', project.get('path_with_namespace', ''))
    project_url = project.get('web_url', project.get('homepage', ''))
    commits = data.get('commits', [])
    total = data.get('total_commits_count', len(commits))

    lines = [
        f"**[代码推送] {project_name}**",
        f"> 分支: **{ref}**",
        f"> 提交者: {user}",
        f"> 提交数: {total}",
    ]

    if commits:
        lines.append("> ")
        for c in commits[:10]:  # 最多显示10条
            cid = c.get('id', '')[:8]
            title = c.get('title', '')
            url = c.get('url', '')
            if url:
                lines.append(f"> - [`{cid}`]({url}) {title}")
            else:
                lines.append(f"> - `{cid}` {title}")
        if len(commits) > 10:
            lines.append(f"> - ...还有 {len(commits) - 10} 条提交")

    if project_url:
        lines.append(f"> ")
        lines.append(f"> [查看仓库]({project_url})")

    return '\n'.join(lines)


def _format_tag_push(data):
    user = data.get('user_name', '未知用户')
    ref = data.get('ref', '').replace('refs/tags/', '')
    project = data.get('project', data.get('repository', {}))
    project_name = project.get('name', '')
    project_url = project.get('web_url', '')

    lines = [
        f"**[标签推送] {project_name}**",
        f"> 标签: **{ref}**",
        f"> 操作者: {user}",
    ]
    if project_url:
        lines.append(f"> ")
        lines.append(f"> [查看仓库]({project_url})")
    return '\n'.join(lines)


def _format_merge_request(data):
    attrs = data.get('object_attributes', {})
    user = data.get('user', {}).get('name', '未知用户')
    title = attrs.get('title', '')
    action = attrs.get('action', '')
    source = attrs.get('source_branch', '')
    target = attrs.get('target_branch', '')
    url = attrs.get('url', '')
    state = attrs.get('state', '')

    action_map = {
        'open': '发起',
        'close': '关闭',
        'reopen': '重新打开',
        'merge': '合并',
        'update': '更新',
    }
    action_cn = action_map.get(action, action)

    lines = [
        f"**[合并请求] {title}**",
        f"> 操作: {action_cn}",
        f"> 分支: {source} → {target}",
        f"> 操作者: {user}",
        f"> 状态: {state}",
    ]
    if url:
        lines.append(f"> ")
        lines.append(f"> [查看详情]({url})")
    return '\n'.join(lines)


def _format_note(data):
    attrs = data.get('object_attributes', {})
    user = data.get('user', {}).get('name', '未知用户')
    note = attrs.get('note', '')
    note_type = attrs.get('noteable_type', '')
    url = attrs.get('url', '')

    # 截断过长的评论
    if len(note) > 200:
        note = note[:200] + '...'

    type_map = {
        'MergeRequest': '合并请求',
        'Commit': '提交',
        'Issue': 'Issue',
        'Snippet': '代码片段',
    }
    type_cn = type_map.get(note_type, note_type)

    lines = [
        f"**[评论] {type_cn}**",
        f"> 评论者: {user}",
        f"> 内容: {note}",
    ]
    if url:
        lines.append(f"> ")
        lines.append(f"> [查看详情]({url})")
    return '\n'.join(lines)


def _format_pipeline(data):
    attrs = data.get('object_attributes', {})
    user = data.get('user', {}).get('name', data.get('commit', {}).get('author', {}).get('name', '未知'))
    project = data.get('project', {})
    project_name = project.get('name', '')
    pipeline_id = attrs.get('id', '')
    status = attrs.get('status', '')
    ref = attrs.get('ref', '')
    url = attrs.get('url', '')

    status_emoji = {
        'success': '✅',
        'failed': '❌',
        'running': '🔄',
        'pending': '⏳',
        'canceled': '⚠️',
        'skipped': '⏭️',
    }
    emoji = status_emoji.get(status, '❓')

    lines = [
        f"**[流水线] {project_name} #{pipeline_id}**",
        f"> 状态: {emoji} {status}",
        f"> 分支: {ref}",
        f"> 触发者: {user}",
    ]

    # 显示失败的 job
    builds = data.get('builds', [])
    failed = [b for b in builds if b.get('status') == 'failed']
    if failed:
        lines.append("> ")
        lines.append("> 失败阶段:")
        for b in failed:
            lines.append(f"> - **{b.get('name', '')}** ({b.get('stage', '')})")

    if url:
        lines.append(f"> ")
        lines.append(f"> [查看详情]({url})")
    return '\n'.join(lines)


def _format_wiki(data):
    user = data.get('user', {}).get('name', '未知用户')
    project = data.get('project', {})
    project_name = project.get('name', '')
    wiki = data.get('object_attributes', {})
    title = wiki.get('title', '')
    url = wiki.get('url', '')

    lines = [
        f"**[Wiki] {project_name}**",
        f"> 标题: {title}",
        f"> 操作者: {user}",
    ]
    if url:
        lines.append(f"> ")
        lines.append(f"> [查看详情]({url})")
    return '\n'.join(lines)


def _format_build(data):
    user = data.get('user', {}).get('name', '未知用户')
    project = data.get('project', {})
    project_name = project.get('name', '')
    build = data.get('builds', [{}])[0] if data.get('builds') else {}
    name = build.get('name', data.get('build_name', ''))
    status = build.get('status', data.get('build_status', ''))

    status_emoji = {
        'success': '✅',
        'failed': '❌',
        'running': '🔄',
        'pending': '⏳',
    }
    emoji = status_emoji.get(status, '❓')

    lines = [
        f"**[构建] {project_name}**",
        f"> 任务: {name}",
        f"> 状态: {emoji} {status}",
        f"> 触发者: {user}",
    ]
    return '\n'.join(lines)


def _format_unknown(data):
    event_type = data.get('object_kind', 'unknown')
    return (
        f"**[未知事件] {event_type}**\n"
        f"> 收到了未支持的事件类型，请检查配置"
    )


# 事件类型 → 格式化函数
_handlers = {
    'push': _format_push,
    'tag_push': _format_tag_push,
    'merge_request': _format_merge_request,
    'note': _format_note,
    'pipeline': _format_pipeline,
    'wiki': _format_wiki,
    'build': _format_build,
}
