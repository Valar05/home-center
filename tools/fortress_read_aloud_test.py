#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import os
import pathlib
import stat
import tempfile

MODULE_PATH=pathlib.Path(__file__).with_name('fortress_read_aloud.py')
spec=importlib.util.spec_from_file_location('fortress_read_aloud',MODULE_PATH)
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def fake_rish(body:str, exit_code:int=0):
    td=tempfile.TemporaryDirectory()
    p=pathlib.Path(td.name)/'rish'
    p.write_text('#!/bin/sh\n'+body+f'\nexit {exit_code}\n',encoding='utf-8')
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return td,p


def run():
    failure=mod.classify_rish_failure('RuntimeException: Server is not running')
    assert failure['kind']=='bridge_server_not_running'
    assert failure['recoveryRoute']=='trusted-wireless-debugging-bootstrap'

    old=os.environ.get('RISH')
    try:
        td,p=fake_rish("echo 'uid=2000(shell) gid=2000(shell)'",0)
        with td:
            os.environ['RISH']=str(p)
            status=mod.bridge_status()
            assert status['serverRunning'] is True
            assert status['clientCallable'] is True
            assert status['shellIdentityAvailable'] is True
            assert status['failureKind']==''

        td,p=fake_rish("echo 'Server is not running' 1>&2",1)
        with td:
            os.environ['RISH']=str(p)
            status=mod.bridge_status()
            assert status['serverRunning'] is False
            assert status['clientCallable'] is False
            assert status['failureKind']=='bridge_server_not_running'
            assert status['recoveryRoute']=='trusted-wireless-debugging-bootstrap'

        td,p=fake_rish("echo 'uid=10234(u0_a234) gid=10234(u0_a234)'",0)
        with td:
            os.environ['RISH']=str(p)
            status=mod.bridge_status()
            assert status['serverRunning'] is True
            assert status['clientCallable'] is True
            assert status['shellIdentityAvailable'] is False
            assert status['failureKind']=='bridge_unexpected_identity'
    finally:
        if old is None: os.environ.pop('RISH',None)
        else: os.environ['RISH']=old

    print('fortress_read_aloud_test: PASS')


if __name__=='__main__': run()
