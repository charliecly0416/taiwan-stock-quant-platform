"""Separately authenticated simulation API; comparison pages never call it."""
from functools import wraps
import os
import re
import sqlite3

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from clean_product.config import load_config, path
from clean_product.paper import PaperStore, auth_secret
from clean_product.service import ProductService


def protected(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        settings = current_app.config.get('PRODUCT_CONFIG') or load_config()
        if settings.get('paper', {}).get('enabled') is not True:
            return jsonify(status='BLOCKED', message='PAPER_DISABLED', simulation_only=True), 503
        token = request.headers.get('Authorization', '')
        secret = current_app.config.get('PAPER_AUTH_SECRET') or auth_secret()
        try:
            if not token.startswith('Bearer ') or len(secret) < 32:
                raise ValueError('missing authorization')
            identity = URLSafeTimedSerializer(secret, salt='tw-clean-paper-v1').loads(token[7:], max_age=3600)
            owner = identity.get('owner')
            if not isinstance(owner, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', owner):
                raise ValueError('invalid owner')
        except (BadSignature, ValueError, TypeError, AttributeError):
            return jsonify(status='BLOCKED', message='PAPER_AUTHENTICATION_REQUIRED', simulation_only=True), 401
        try:
            g.paper_owner, g.product_config = owner, settings
            g.paper_store = PaperStore(path(settings['paper']['store']))
            return fn(*args, **kwargs)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            message = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r'(PAPER|MODEL)_[A-Z_]+', str(exc)) else 'PAPER_INPUT_OR_ARTIFACT_INVALID'
            return jsonify(status='BLOCKED', message=message, simulation_only=True), 409
        except sqlite3.Error:
            return jsonify(status='BLOCKED', message='PAPER_STORE_UNAVAILABLE', simulation_only=True), 503
    return call


def body(fields):
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('PAPER_REQUEST_FIELDS_INVALID')
    for key, item in value.items():
        if key == 'confirm':
            valid = type(item) is bool
        elif key == 'epoch':
            valid = type(item) is int and item >= 1
        elif key == 'initial_cash':
            valid = type(item) in (str, int, float) and len(str(item)) <= 40
        else:
            valid = isinstance(item, str) and 1 <= len(item) <= 100
        if not valid: raise ValueError('PAPER_REQUEST_FIELDS_INVALID')
    return value


def register_paper_routes(app):
    @app.get('/api/tw-stock/sim/accounts')
    @protected
    def accounts():
        return jsonify(status='READY', accounts=g.paper_store.accounts(g.paper_owner), simulation_only=True)

    @app.post('/api/tw-stock/sim/accounts')
    @protected
    def create():
        value = body(['name', 'initial_cash', 'key'])
        return jsonify(g.paper_store.create(g.paper_owner, **value))

    @app.get('/api/tw-stock/paper-portfolio/state')
    @protected
    def state():
        return jsonify(g.paper_store.state(g.paper_owner, request.args.get('paper_account_id', '')))

    @app.get('/api/tw-stock/paper-portfolio/apply-runs')
    @protected
    def history():
        return jsonify(status='READY', runs=g.paper_store.history(g.paper_owner, request.args.get('paper_account_id', '')), simulation_only=True)

    @app.post('/api/tw-stock/paper-portfolio/preview')
    @protected
    def preview():
        value = body(['paper_account_id', 'date'])
        from datetime import date
        if date.fromisoformat(value['date']).isoformat() != value['date']: raise ValueError('PAPER_DATE_INVALID')
        return jsonify(g.paper_store.preview(g.paper_owner, value['paper_account_id'], value['date'], ProductService(g.product_config)))

    @app.post('/api/tw-stock/paper-portfolio/apply-decision')
    @protected
    def apply():
        value = body(['decision_id', 'input_checksum', 'epoch', 'key', 'confirm'])
        return jsonify(g.paper_store.apply(g.paper_owner, **value))

    @app.post('/api/tw-stock/paper-portfolio/reset')
    @protected
    def reset():
        value = body(['paper_account_id', 'epoch', 'key', 'confirm'])
        account = value.pop('paper_account_id')
        return jsonify(g.paper_store.reset(g.paper_owner, account, **value))
