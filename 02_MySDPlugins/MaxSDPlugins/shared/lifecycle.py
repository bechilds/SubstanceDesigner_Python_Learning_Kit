# -*- coding: utf-8 -*-
"""统一管理非模态窗口，供插件卸载及独立导出物清理使用。"""

from .. import sdcompat

_dialogs = {}


def _alive(dialog):
    checker = sdcompat._isvalid_fn()
    return dialog is not None and (checker is None or checker(dialog))


def show_dialog(key, factory, owner=None):
    """复用存活窗口；关闭时释放，并同步旧模块的 _dialog_ref。"""
    if sdcompat.QtWidgets is None:
        return None
    dialog = _dialogs.get(key)
    try:
        if not _alive(dialog):
            dialog = factory()
            dialog.setAttribute(sdcompat.QtCore.Qt.WA_DeleteOnClose, True)
            _dialogs[key] = dialog
            if owner is not None:
                owner['_dialog_ref'] = dialog

            def forget(*_args):
                # 延迟销毁旧窗口时，不得清掉刚创建的新窗口。
                if _dialogs.get(key) is dialog:
                    _dialogs.pop(key, None)
                if owner is not None and owner.get('_dialog_ref') is dialog:
                    owner['_dialog_ref'] = None

            dialog.finished.connect(forget)
            dialog.destroyed.connect(forget)
        if dialog.isMinimized():
            dialog.showNormal()
        else:
            dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog
    except sdcompat.SD_API_ERRORS as error:
        print(f'[MaxSDPlugin/lifecycle] 打开 {key} 失败: {sdcompat.error_text(error)}')
        raise


def busy_dialogs():
    """正在执行 SD 任务的窗口不允许在 processEvents 中途被卸载。"""
    return [key for key, dialog in list(_dialogs.items())
            if _alive(dialog) and getattr(dialog, '_running', False)]


def close_all_dialogs():
    """成功关闭全部窗口返回 True；有任务运行或拒绝关闭时返回 False。"""
    busy = busy_dialogs()
    if busy:
        print('[MaxSDPlugin/lifecycle] 请先取消或等待任务完成: ' + ', '.join(busy))
        return False
    success = True
    for key, dialog in list(_dialogs.items()):
        try:
            if _alive(dialog) and dialog.close() is False:
                success = False
        except sdcompat.SD_API_ERRORS as error:
            success = False
            print(f'[MaxSDPlugin/lifecycle] 关闭 {key} 失败: {sdcompat.error_text(error)}')
    return success
