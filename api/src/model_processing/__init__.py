"""
初始化model_processing模块
提供模型处理相关功能

注意：在Windows环境中，需要使用conda安装OpenCASCADE依赖：
conda install -c conda-forge pythonocc-core
"""

# 检查OpenCASCADE依赖是否可用
try:
    from OCC.Core.GProp import GProp_GProps
    OPENCASCADE_AVAILABLE = True
except ImportError:
    import warnings
    warnings.warn(
        "OpenCASCADE依赖未安装，3D模型处理功能将不可用。\n"
        "在Windows环境中，请使用conda安装：\n"
        "conda install -c conda-forge pythonocc-core"
    )
    OPENCASCADE_AVAILABLE = False
