"""GitLab → 企业微信机器人 中转服务"""
import logging
import secrets
from flask import Flask, request, jsonify, render_template, redirect, url_for
from config import PORT
import models
from handlers.gitlab import parse_event, format_message
from handlers.wechat import send_markdown, send_test

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ---------- 初始化 ----------

@app.before_request
def ensure_db():
    """确保数据库已初始化"""
    if not hasattr(app, '_db_inited'):
        models.init_db()
        app._db_inited = True


# ---------- GitLab Webhook 入口 ----------

@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    """接收 GitLab webhook 并转发到企业微信"""
    # 查找映射
    mapping = models.get_mapping_by_token(token)
    if not mapping:
        return jsonify({'error': '无效的 webhook token'}), 404

    # 检查事件类型
    data = request.json
    if not data:
        return jsonify({'error': '请求体为空'}), 400

    event_type, project_name = parse_event(data)

    # 检查是否需要处理该事件
    allowed_events = mapping.get('events', '*')
    if allowed_events != '*':
        allowed = [e.strip() for e in allowed_events.split(',')]
        if event_type not in allowed:
            logger.info(f"跳过事件 {event_type}，不在允许列表中")
            return jsonify({'status': 'skipped', 'reason': 'event not in allowed list'}), 200

    # 格式化消息
    content = format_message(data)
    logger.info(f"收到事件: {event_type}, 项目: {project_name}")

    # 发送到企业微信
    success, msg = send_markdown(mapping['wechat_url'], content)

    # 记录日志
    models.add_log(
        mapping_id=mapping['id'],
        event_type=event_type,
        project=project_name,
        status='success' if success else 'failed',
        message=msg
    )

    if success:
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'status': 'error', 'message': msg}), 500


# ---------- 管理页面 ----------

@app.route('/')
def index():
    """配置管理首页"""
    mappings = models.get_all_mappings()
    return render_template('index.html', mappings=mappings)


@app.route('/mapping/add', methods=['POST'])
def add_mapping():
    """新增映射"""
    name = request.form.get('name', '').strip()
    gitlab_token = request.form.get('gitlab_token', '').strip()
    wechat_url = request.form.get('wechat_url', '').strip()
    events = request.form.get('events', '*').strip()

    if not name or not wechat_url:
        return redirect(url_for('index'))

    # 如果没填 token，自动生成
    if not gitlab_token:
        gitlab_token = secrets.token_urlsafe(16)

    try:
        models.add_mapping(name, gitlab_token, wechat_url, events)
    except Exception as e:
        logger.error(f"新增映射失败: {e}")
        # token 重复等错误
        pass

    return redirect(url_for('index'))


@app.route('/mapping/<int:mapping_id>/edit', methods=['POST'])
def edit_mapping(mapping_id):
    """编辑映射"""
    name = request.form.get('name', '').strip()
    gitlab_token = request.form.get('gitlab_token', '').strip()
    wechat_url = request.form.get('wechat_url', '').strip()
    events = request.form.get('events', '*').strip()
    enabled = 1 if request.form.get('enabled') else 0

    if not name or not wechat_url:
        return redirect(url_for('index'))

    models.update_mapping(mapping_id, name, gitlab_token, wechat_url, events, enabled)
    return redirect(url_for('index'))


@app.route('/mapping/<int:mapping_id>/delete', methods=['POST'])
def delete_mapping(mapping_id):
    """删除映射"""
    models.delete_mapping(mapping_id)
    return redirect(url_for('index'))


@app.route('/mapping/<int:mapping_id>/test', methods=['POST'])
def test_mapping(mapping_id):
    """发送测试消息"""
    mapping = models.get_mapping_by_id(mapping_id)
    if not mapping:
        return jsonify({'status': 'error', 'message': '映射不存在'}), 404

    success, msg = send_test(mapping['wechat_url'])
    return jsonify({'status': 'ok' if success else 'error', 'message': msg})


# ---------- 日志页面 ----------

@app.route('/logs')
def logs():
    """推送日志页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    all_logs = models.get_logs(limit=200)
    total = len(all_logs)
    start = (page - 1) * per_page
    end = start + per_page
    page_logs = all_logs[start:end]
    total_pages = (total + per_page - 1) // per_page

    return render_template('log.html',
                           logs=page_logs,
                           page=page,
                           total_pages=total_pages,
                           total=total)


# ---------- API 接口 ----------

@app.route('/api/mappings', methods=['GET'])
def api_mappings():
    """获取所有映射（JSON）"""
    return jsonify(models.get_all_mappings())


@app.route('/api/generate_token', methods=['GET'])
def api_generate_token():
    """生成随机 token"""
    return jsonify({'token': secrets.token_urlsafe(16)})


# ---------- 启动 ----------

if __name__ == '__main__':
    models.init_db()
    logger.info(f"服务启动，监听端口 {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
