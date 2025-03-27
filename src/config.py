"""
配置文件和参数管理
包含系统的各种参数设置和配置管理功能
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("config")

# 默认配置
DEFAULT_CONFIG = {
    # 体素化参数
    "voxelization": {
        "base_voxel_size": 1.0,           # 基础体素大小 (m³)
        "min_voxel_size": 0.125,          # 最小体素大小 (m³)
        "curvature_threshold": 0.5,        # 触发体素细化的曲率阈值 (/m)
        "width_threshold": 2.0,            # 触发体素细化的宽度阈值 (m)
        "use_gpu_acceleration": True,      # 是否使用GPU加速
        "max_memory_usage": 8192,          # 最大内存使用 (MB)
    },
    
    # 空间识别参数
    "space_detection": {
        "min_space_volume": 5.0,           # 识别为独立空间的最小体积 (m³)
        "space_merge_distance": 0.5,       # 合并相近空间的阈值距离 (m)
        "min_passage_height": 1.8,         # 人员可通行的最小高度 (m)
        "max_seed_points": 5000,           # 最大种子点数量
        "flood_fill_step": 0.5,            # 洪水填充步长 (m)
    },
    
    # 通道与门参数
    "openings": {
        "standard_door_area_limit": 2.0,   # 标准门的最大面积 (m²)
        "wide_door_area_limit": 5.0,       # 宽门/双开门的最大面积 (m²)
        "passage_aspect_ratio": 3.0,       # 识别为通道的长宽比阈值
        "connection_degree_threshold": 3,  # 识别为通道的最小连接数
        "opening_height_range": [0.0, 2.2] # 有效开口的高度范围 (m)
    },
    
    # 通风率参数
    "ventilation": {
        "high_ach_rate": 10.0,             # 直接与外界相连的通风率 (ACH)
        "medium_ach_range": [5.0, 8.0],    # 一级相连的通风率范围 (ACH)
        "low_ach_range": [1.0, 4.0],       # 多级相连的通风率范围 (ACH)
        "opening_influence_factor": 0.7,   # 开口面积对通风率的影响权重
        "path_decay_factor": 0.6,          # 每增加一级连接的通风衰减因子
    },
    
    # 处理选项
    "processing": {
        "num_threads": 8,                  # 并行处理线程数
        "enable_parallel": True,           # 是否启用并行处理
        "chunk_size": 1000,                # 并行处理块大小
        "enable_incremental_update": True, # 是否启用增量更新
    },
    
    # 文件和路径
    "paths": {
        "models_dir": "data/models",       # 模型文件目录
        "results_dir": "data/results",     # 结果保存目录
        "temp_dir": "data/temp",           # 临时文件目录
    }
}


class Config:
    """配置管理类，用于管理系统的各种参数设置"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.config = DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.info("Using default configuration")
            
        # 确保目录存在
        self._ensure_directories()
    
    def load_config(self, config_path: str) -> None:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                
            # 递归更新配置，保留默认值
            self._update_dict_recursive(self.config, user_config)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件保存路径，如果为None则使用初始化时的路径
        """
        save_path = config_path or self.config_path
        if not save_path:
            logger.warning("No path specified for saving configuration")
            return
            
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, section: str, key: Optional[str] = None) -> Any:
        """
        获取配置项的值
        
        Args:
            section: 配置部分名称
            key: 配置项名称，如果为None则返回整个部分
            
        Returns:
            配置项的值
        """
        if section not in self.config:
            logger.warning(f"Section '{section}' not found in configuration")
            return None
            
        if key is None:
            return self.config[section]
            
        if key not in self.config[section]:
            logger.warning(f"Key '{key}' not found in section '{section}'")
            return None
            
        return self.config[section][key]
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        设置配置项的值
        
        Args:
            section: 配置部分名称
            key: 配置项名称
            value: 配置项的值
        """
        if section not in self.config:
            self.config[section] = {}
            
        self.config[section][key] = value
        logger.info(f"Configuration updated: {section}.{key} = {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            所有配置的副本
        """
        return self.config.copy()
    
    def _update_dict_recursive(self, target: Dict, source: Dict) -> None:
        """
        递归更新嵌套字典，保留目标字典中存在但源字典中不存在的键
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_dict_recursive(target[key], value)
            else:
                target[key] = value
    
    def _ensure_directories(self) -> None:
        """确保配置中指定的目录存在"""
        for key, path in self.config["paths"].items():
            if key.endswith('_dir'):
                os.makedirs(path, exist_ok=True)
                logger.debug(f"Ensured directory exists: {path}")


# 全局配置实例
_config_instance = None

def get_config(config_path: Optional[str] = None) -> Config:
    """
    获取全局配置实例
    
    Args:
        config_path: 配置文件路径，只在首次调用时有效
        
    Returns:
        全局配置实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


if __name__ == "__main__":
    # 测试配置功能
    config = get_config()
    print("默认基础体素大小:", config.get("voxelization", "base_voxel_size"))
    
    # 修改配置
    config.set("voxelization", "base_voxel_size", 0.75)
    print("修改后基础体素大小:", config.get("voxelization", "base_voxel_size"))