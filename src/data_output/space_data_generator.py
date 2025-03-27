#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: src/data_output/space_data_generator.py
空间数据生成器
整合空间几何、功能和通风特性数据，生成标准格式的空间描述
"""

import os
import logging
import time
import json
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
import networkx as nx
from datetime import datetime

# 本地模块导入
from ..config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("space_data_generator")


class SpaceDataGenerator:
    """空间数据生成器，整合分析结果生成标准输出"""
    
    def __init__(self):
        """初始化空间数据生成器"""
        self.config = get_config()
        
        # 获取输出路径
        self.results_dir = self.config.get("paths", "results_dir")
        
        # 确保结果目录存在
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info(f"初始化空间数据生成器，结果目录: {self.results_dir}")
    
    def generate_space_data(self, spaces: List[Dict[str, Any]], 
                          openings: List[Dict[str, Any]],
                          ach_rates: Dict[str, float],
                          ventilation_paths: Dict[str, List[Dict[str, Any]]],
                          space_graph: nx.Graph) -> Dict[str, Any]:
        """
        整合分析结果，生成标准格式的空间数据
        
        Args:
            spaces: 空间列表
            openings: 开口列表
            ach_rates: 空间通风率字典
            ventilation_paths: 空间通风路径字典
            space_graph: 空间连接图
            
        Returns:
            生成的完整数据
        """
        start_time = time.time()
        logger.info("开始生成空间数据")
        
        # 创建结果数据结构
        result_data = {
            "metadata": self._generate_metadata(),
            "spaces": self._process_spaces(spaces, ach_rates, ventilation_paths),
            "connections": self._process_openings(openings),
            "ventilationPaths": self._process_ventilation_paths(ventilation_paths)
        }
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"空间数据生成完成，耗时: {elapsed_time:.2f}秒")
        
        return result_data
    
    def save_space_data(self, data: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """
        保存空间数据到文件
        
        Args:
            data: 空间数据
            file_name: 文件名（可选，默认自动生成）
            
        Returns:
            保存的文件路径
        """
        # 如果未指定文件名，生成带时间戳的默认文件名
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"space_data_{timestamp}.json"
        
        # 确保文件扩展名
        if not file_name.endswith(".json"):
            file_name += ".json"
        
        # 完整文件路径
        file_path = os.path.join(self.results_dir, file_name)
        
        # 保存数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"空间数据已保存到: {file_path}")
        
        return file_path
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """
        生成元数据
        
        Returns:
            元数据字典
        """
        return {
            "version": "1.0",
            "generatedAt": datetime.now().isoformat(),
            "description": "海上平台空间分析结果",
            "parameters": {
                "voxelization": {
                    "baseSize": self.config.get("voxelization", "base_voxel_size"),
                    "minSize": self.config.get("voxelization", "min_voxel_size")
                },
                "ventilation": {
                    "highAch": self.config.get("ventilation", "high_ach_rate"),
                    "mediumAchRange": self.config.get("ventilation", "medium_ach_range"),
                    "lowAchRange": self.config.get("ventilation", "low_ach_range")
                }
            }
        }
    
    def _process_spaces(self, spaces: List[Dict[str, Any]], 
                      ach_rates: Dict[str, float],
                      ventilation_paths: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        处理空间数据
        
        Args:
            spaces: 空间列表
            ach_rates: 空间通风率字典
            ventilation_paths: 空间通风路径字典
            
        Returns:
            处理后的空间数据列表
        """
        processed_spaces = []
        
        for space in spaces:
            space_id = space["id"]
            
            # 获取通风率
            ach_rate = ach_rates.get(space_id, 0)
            
            # 获取连接的开口
            connections = []
            
            # 通风路径信息
            ventilation_info = {}
            paths = ventilation_paths.get(space_id, [])
            if paths:
                # 提取主要路径
                primary_path = paths[0]
                ventilation_info = {
                    "primaryPath": {
                        "route": primary_path["route"],
                        "via": primary_path["via"],
                        "length": primary_path["length"]
                    },
                    "pathCount": len(paths)
                }
            
            # 创建标准化空间对象
            processed_space = {
                "id": space_id,
                "type": space.get("type", "unknown"),
                "volume": space.get("volume", 0),
                "boundingBox": {
                    "min": space.get("bbox_min", [0, 0, 0]),
                    "max": space.get("bbox_max", [0, 0, 0])
                },
                "ventilationRate": ach_rate,
                "connections": connections,  # 将在后续填充
                "ventilationInfo": ventilation_info
            }
            
            processed_spaces.append(processed_space)
        
        return processed_spaces
    
    def _process_openings(self, openings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理开口数据
        
        Args:
            openings: 开口列表
            
        Returns:
            处理后的开口数据列表
        """
        processed_openings = []
        
        for opening in openings:
            # 创建标准化开口对象
            processed_opening = {
                "id": opening["id"],
                "type": opening.get("type", "unknown"),
                "connects": opening.get("connects", []),
                "position": opening.get("position", [0, 0, 0]),
                "area": opening.get("area", 0),
                "state": opening.get("state", "open")
            }
            
            processed_openings.append(processed_opening)
            
            # 更新相连空间的connections属性
            for space_id in opening.get("connects", []):
                # 查找空间
                for space in self._process_spaces:
                    if space["id"] == space_id:
                        if opening["id"] not in space["connections"]:
                            space["connections"].append(opening["id"])
                        break
        
        return processed_openings
    
    def _process_ventilation_paths(self, ventilation_paths: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        处理通风路径数据
        
        Args:
            ventilation_paths: 空间通风路径字典
            
        Returns:
            处理后的通风路径数据列表
        """
        processed_paths = []
        
        for space_id, paths in ventilation_paths.items():
            # 每个空间的通风路径
            space_paths = []
            
            # 计算总贡献
            total_contribution = 0
            path_contributions = []
            
            for path in paths:
                # 计算路径贡献（基于权重的倒数）
                contribution = 1.0 / (path["weight"] + 0.1)
                path_contributions.append(contribution)
                total_contribution += contribution
            
            # 归一化贡献率
            normalized_contributions = [c / total_contribution for c in path_contributions] if total_contribution > 0 else []
            
            # 处理每条路径
            for i, (path, contribution) in enumerate(zip(paths, normalized_contributions)):
                space_paths.append({
                    "route": path["route"],
                    "via": path["via"],
                    "contribution": contribution
                })
            
            # 添加到结果
            if space_paths:
                processed_paths.append({
                    "spaceId": space_id,
                    "paths": space_paths
                })
        
        return processed_paths
    
    def generate_simplified_geometry(self, spaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成用于可视化的简化几何表示
        
        Args:
            spaces: 空间列表
            
        Returns:
            简化几何数据
        """
        geometry_data = {}
        
        for space in spaces:
            space_id = space["id"]
            
            # 从包围盒创建简化几何
            bbox_min = space.get("bbox_min", [0, 0, 0])
            bbox_max = space.get("bbox_max", [0, 0, 0])
            
            # 计算盒子的8个顶点
            vertices = [
                [bbox_min[0], bbox_min[1], bbox_min[2]],
                [bbox_max[0], bbox_min[1], bbox_min[2]],
                [bbox_min[0], bbox_max[1], bbox_min[2]],
                [bbox_max[0], bbox_max[1], bbox_min[2]],
                [bbox_min[0], bbox_min[1], bbox_max[2]],
                [bbox_max[0], bbox_min[1], bbox_max[2]],
                [bbox_min[0], bbox_max[1], bbox_max[2]],
                [bbox_max[0], bbox_max[1], bbox_max[2]]
            ]
            
            # 定义6个面
            faces = [
                [0, 1, 3, 2],  # 底面
                [4, 5, 7, 6],  # 顶面
                [0, 1, 5, 4],  # 前面
                [2, 3, 7, 6],  # 后面
                [0, 2, 6, 4],  # 左面
                [1, 3, 7, 5]   # 右面
            ]
            
            # 添加到几何数据
            geometry_data[space_id] = {
                "vertices": vertices,
                "faces": faces,
                "type": space.get("type", "unknown")
            }
        
        return geometry_data
    
    def export_for_visualization(self, data: Dict[str, Any], 
                               file_name: Optional[str] = None) -> str:
        """
        导出适用于可视化的数据
        
        Args:
            data: 空间数据
            file_name: 文件名（可选，默认自动生成）
            
        Returns:
            保存的文件路径
        """
        # 如果未指定文件名，生成带时间戳的默认文件名
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"visualization_data_{timestamp}.json"
        
        # 确保文件扩展名
        if not file_name.endswith(".json"):
            file_name += ".json"
        
        # 完整文件路径
        file_path = os.path.join(self.results_dir, file_name)
        
        # 提取可视化数据
        spaces = data.get("spaces", [])
        connections = data.get("connections", [])
        
        # 创建简化几何
        geometry = self.generate_simplified_geometry(spaces)
        
        # 创建可视化数据
        viz_data = {
            "spaces": [{
                "id": space["id"],
                "type": space.get("type", "unknown"),
                "ventilationRate": space.get("ventilationRate", 0),
                "geometry": geometry.get(space["id"], {})
            } for space in spaces],
            
            "connections": [{
                "id": conn["id"],
                "type": conn.get("type", "unknown"),
                "connects": conn.get("connects", []),
                "position": conn.get("position", [0, 0, 0]),
                "state": conn.get("state", "open")
            } for conn in connections]
        }
        
        # 保存数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(viz_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"可视化数据已保存到: {file_path}")
        
        return file_path
    
    def validate_space_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        验证空间数据的完整性和一致性
        
        Args:
            data: 空间数据
            
        Returns:
            验证结果，包含错误和警告
        """
        errors = []
        warnings = []
        
        # 检查空间
        spaces = data.get("spaces", [])
        space_ids = set()
        
        for space in spaces:
            # 检查必需字段
            if "id" not in space:
                errors.append("发现没有ID的空间")
                continue
                
            # 检查ID唯一性
            if space["id"] in space_ids:
                errors.append(f"发现重复的空间ID: {space['id']}")
            space_ids.add(space["id"])
            
            # 检查体积合理性
            volume = space.get("volume", 0)
            if volume <= 0:
                warnings.append(f"空间 {space['id']} 的体积不合理: {volume}")
            
            # 检查通风率合理性
            ach = space.get("ventilationRate", 0)
            if ach < 0:
                warnings.append(f"空间 {space['id']} 的通风率为负: {ach}")
            elif ach > 20:
                warnings.append(f"空间 {space['id']} 的通风率过高: {ach}")
        
        # 检查连接
        connections = data.get("connections", [])
        conn_ids = set()
        
        for conn in connections:
            # 检查必需字段
            if "id" not in conn:
                errors.append("发现没有ID的连接")
                continue
                
            # 检查ID唯一性
            if conn["id"] in conn_ids:
                errors.append(f"发现重复的连接ID: {conn['id']}")
            conn_ids.add(conn["id"])
            
            # 检查连接的空间存在
            connects = conn.get("connects", [])
            for space_id in connects:
                if space_id not in space_ids and not space_id.startswith("space_exterior"):
                    errors.append(f"连接 {conn['id']} 引用了不存在的空间: {space_id}")
        
        # 返回验证结果
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }


if __name__ == "__main__":
    # 测试空间数据生成器
    generator = SpaceDataGenerator()
    
    # 创建测试数据
    # 假设空间
    spaces = [
        {"id": "space_001", "volume": 100, "center": [5, 5, 3], "dimensions": [10, 10, 3], "type": "room", 
         "bbox_min": [0, 0, 0], "bbox_max": [10, 10, 6]},
        {"id": "space_002", "volume": 80, "center": [15, 5, 3], "dimensions": [8, 10, 3], "type": "corridor", 
         "bbox_min": [10, 0, 0], "bbox_max": [18, 10, 6]},
    ]
    
    # 假设开口
    openings = [
        {"id": "opening_001", "connects": ["space_001", "space_002"], "area": 2.0, "type": "door", 
         "position": [10, 5, 3]},
        {"id": "opening_002", "connects": ["space_001", "space_exterior"], "area": 1.5, "type": "window", 
         "position": [0, 5, 3]},
    ]
    
    # 假设通风率
    ach_rates = {
        "space_001": 8.5,
        "space_002": 5.2
    }
    
    # 假设通风路径
    ventilation_paths = {
        "space_001": [
            {"route": ["space_001", "space_exterior"], "via": ["opening_002"], "weight": 0.5, "length": 1, 
             "decay_factor": 1.0, "total_opening_area": 1.5},
        ],
        "space_002": [
            {"route": ["space_002", "space_001", "space_exterior"], "via": ["opening_001", "opening_002"], 
             "weight": 1.0, "length": 2, "decay_factor": 0.6, "total_opening_area": 3.5},
        ]
    }
    
    # 创建测试图
    space_graph = nx.Graph()
    space_graph.add_nodes_from(["space_001", "space_002", "space_exterior"])
    space_graph.add_edges_from([("space_001", "space_002"), ("space_001", "space_exterior")])
    
    # 生成空间数据
    data = generator.generate_space_data(spaces, openings, ach_rates, ventilation_paths, space_graph)
    
    # 验证数据
    validation = generator.validate_space_data(data)
    print(f"数据验证结果: {'有效' if validation['is_valid'] else '无效'}")
    if validation["errors"]:
        print("错误:")
        for error in validation["errors"]:
            print(f"  - {error}")
    if validation["warnings"]:
        print("警告:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
    
    # 导出数据
    file_path = generator.save_space_data(data, "test_space_data.json")
    print(f"数据已保存到: {file_path}")
    
    # 导出可视化数据
    viz_path = generator.export_for_visualization(data, "test_visualization.json")
    print(f"可视化数据已保存到: {viz_path}")