from flask import render_template,request

from . import core

@core.route('/')
@core.route('/index')
def index():
    return render_template('index.html')

@core.route('/info')
def info():
    return render_template('info.html')
