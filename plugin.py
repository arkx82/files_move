# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback

# third-party
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit, send
from flask_login import login_user, logout_user, current_user, login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_data, socketio, check_api
from framework.util import Util
from system.model import ModelSetting as SystemModelSetting
from system.logic import SystemLogic
from framework.common.torrent.process import TorrentProcess

# 패키지
# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

from .model import ModelSetting, ModelMediaItem
from .logic import Logic
from .logic_normal import LogicNormal

#########################################################


#########################################################
# 플러그인 공용
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

menu = {
    'main' : [package_name, '파일정리'],
    'sub' : [
        ['setting', '설정'], ['list', '목록'], ['log', '로그']
    ],
    'category' : 'fileprocess'
}

plugin_info = {
    'version' : '0.1.0.0',
    'name' : 'files_move',
    'category_name' : 'fileprocess',
    'developer' : 'arkx82',
    'description' : '구글 드라이브 파일 정리',
    'home' : 'https://github.com/arkx82/files_move',
    'more' : '',
}

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

def process_telegram_data(data):
    pass

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/list' % package_name)

@blueprint.route('/<sub>')
@login_required
def first_menu(sub):
    arg = ModelSetting.to_dict()
    arg['package_name'] = package_name
    if sub == 'setting':
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'list':
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'manage':
        return render_template('/manage/%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    try:
        # 설정
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            return jsonify(ret)
        elif sub == 'scheduler':
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        elif sub == 'filelist':
            ret = Logic.fileList(request)
            return jsonify(ret)
        elif sub == 'one_execute':
            ret = Logic.one_execute()
            return jsonify(ret)
        elif sub == 'reset_db':
            ret = Logic.reset_db()
            return jsonify(ret)

    except Exception as e:
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())
        return jsonify('fail')

