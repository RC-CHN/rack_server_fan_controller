from .. import models
from .base import BaseServerController
from .r730 import R730Controller

# 注册所有可用的控制器
# 键是服务器型号 (小写)，值是控制器类
CONTROLLER_MAP = {
    "r730": R730Controller,
}

class UnsupportedModelError(Exception):
    """当服务器型号不被支持时抛出此异常。"""
    pass

def get_controller(server: models.Server) -> BaseServerController:
    """
    控制器工厂函数。
    根据服务器型号返回一个具体的控制器实例。
    
    :param server: 服务器的 SQLAlchemy 模型实例。
    :return: 一个 BaseServerController 的子类实例。
    :raises UnsupportedModelError: 如果服务器型号不被支持。
    """
    model_key = server.model.lower()
    controller_class = CONTROLLER_MAP.get(model_key)

    if not controller_class:
        raise UnsupportedModelError(f"Server model '{server.model}' is not supported.")

    return controller_class(server)