"""
File: src/ventilation/ach_calculator.py
通风率计算引擎
基于空间拓扑和通风路径计算通风率(ACH)
"""

import os
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
import networkx as nx
from collections import defaultdict

# 本地模块导入
from ..config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ach_calculator")


class AchCalculator:
    """通风率计算引擎，计算空间的通风率(ACH)"""
    
    def __init__(self):
        """初始化通风率计算引擎"""
        self.config = get_config()
        
        # 获取通风率参数
        self.high_ach = self.config.get("ventilation", "high_ach_rate")
        self.medium_ach_range = self.config.get("ventilation", "medium_ach_range")
        self.low_ach_range = self.config.get("ventilation", "low_ach_range")
        self.opening_influence = self.config.get("ventilation", "opening_influence_factor")
        self.path_decay = self.config.get("ventilation", "path_decay_factor")
        
        # 存储计算结果
        self.ach_rates = {}  # 空间通风率
        self.ventilation_paths = {}  # 空间通风路径
        
        logger.info(f"初始化通风率计算引擎，高通风率={self.high_ach} ACH")
    
    def calculate_ach_rates(self, spaces: List[Dict[str, Any]], 
                          space_graph: nx.Graph, exterior_nodes: List[str]) -> Dict[str, Any]:
        """
        计算各空间的通风率(ACH)
        
        Args:
            spaces: 空间列表
            space_graph: 空间连接图
            exterior_nodes: 外部空间节点列表
            
        Returns:
            通风率计算结果
        """
        start_time = time.time()
        logger.info("开始计算通风率")
        
        # 重置存储
        self.ach_rates = {}
        self.ventilation_paths = {}
        
        # 创建空间ID到空间对象的映射
        space_map = {space["id"]: space for space in spaces}
        
        # 对每个空间计算通风率
        for space in spaces:
            space_id = space["id"]
            
            # 计算到外部空间的通风路径
            paths_to_exterior = self._find_ventilation_paths(
                space_id, space_graph, exterior_nodes
            )
            
            # 存储通风路径
            self.ventilation_paths[space_id] = paths_to_exterior
            
            # 计算通风率
            ach_rate = self._calculate_space_ach(
                space, paths_to_exterior, space_graph, space_map
            )
            
            # 存储结果
            self.ach_rates[space_id] = ach_rate
            
            logger.debug(f"空间 {space_id} 通风率: {ach_rate:.2f} ACH")
        
        # 检验通风率的物理合理性并调整
        self._validate_ach_rates(space_graph)
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"通风率计算完成，耗时: {elapsed_time:.2f}秒")
        
        return {
            "ach_rates": self.ach_rates,
            "ventilation_paths": self.ventilation_paths,
            "elapsed_time": elapsed_time
        }
    
    def _find_ventilation_paths(self, space_id: str, space_graph: nx.Graph, 
                               exterior_nodes: List[str]) -> List[Dict[str, Any]]:
        """
        找到指定空间到外部的通风路径
        
        Args:
            space_id: 空间ID
            space_graph: 空间连接图
            exterior_nodes: 外部空间节点列表
            
        Returns:
            通风路径列表
        """
        ventilation_paths = []
        
        # 对每个外部节点
        for ext_id in exterior_nodes:
            # 检查是否存在路径
            if not nx.has_path(space_graph, space_id, ext_id):
                continue
                
            # 尝试找到所有可能的简单路径（有限数量）
            # 这里使用简单路径而非最短路径，以考虑多种通风可能性
            try:
                # 限制路径长度和数量，避免计算过多
                # 在实际建筑中，通风路径通常不会太长
                all_paths = list(nx.all_simple_paths(
                    space_graph, space_id, ext_id, cutoff=6
                ))
                
                # 限制路径数量
                max_paths = 5
                all_paths = all_paths[:max_paths]
                
                # 处理每条路径
                for path in all_paths:
                    # 计算路径权重和开口特性
                    path_weight = 0
                    openings_info = []
                    total_opening_area = 0
                    
                    # 检查路径上的每条边
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        edge_data = space_graph.get_edge_data(u, v)
                        
                        # 累加权重
                        edge_weight = edge_data.get("weight", 1.0)
                        path_weight += edge_weight
                        
                        # 收集开口信息
                        for opening_id in edge_data.get("openings", []):
                            opening_type = next((t for t in edge_data.get("opening_types", []) 
                                              if t != "repair"), "unknown")
                            
                            # 估算开口面积（如果边数据中没有直接提供）
                            # 权重通常与面积成反比
                            opening_area = 1.0 / edge_weight if edge_weight > 0 else 1.0
                            total_opening_area += opening_area
                            
                            openings_info.append({
                                "id": opening_id,
                                "type": opening_type,
                                "estimated_area": opening_area
                            })
                    
                    # 计算路径衰减因子（取决于路径长度）
                    # 路径越长，贡献越小
                    path_length = len(path) - 1
                    decay_factor = self.path_decay ** (path_length - 1)
                    
                    # 创建路径对象
                    path_obj = {
                        "route": path,
                        "via": [o["id"] for o in openings_info],
                        "openings": openings_info,
                        "weight": path_weight,
                        "length": path_length,
                        "decay_factor": decay_factor,
                        "total_opening_area": total_opening_area,
                        "exterior": ext_id
                    }
                    
                    ventilation_paths.append(path_obj)
            except nx.NetworkXError:
                # 处理可能的错误
                pass
                
        # 按权重排序（权重小的优先）
        ventilation_paths.sort(key=lambda p: p["weight"])
        
        return ventilation_paths
    
    def _calculate_space_ach(self, space: Dict[str, Any], paths: List[Dict[str, Any]],
                           space_graph: nx.Graph, space_map: Dict[str, Dict[str, Any]]) -> float:
        """
        计算单个空间的通风率
        
        Args:
            space: 空间对象
            paths: 通风路径列表
            space_graph: 空间连接图
            space_map: 空间ID到空间对象的映射
            
        Returns:
            计算的通风率（ACH）
        """
        # 如果没有通风路径，返回最低通风率
        if not paths:
            return self.low_ach_range[0]
        
        # 获取空间体积
        volume = space.get("volume", 1.0)
        
        # 分析通风路径
        path_contributions = []
        
        for path in paths:
            # 计算路径长度
            path_length = path["length"]
            
            # 根据路径长度确定基础通风率
            if path_length == 1:
                # 直接连接到外部
                base_ach = self.high_ach
            elif path_length == 2:
                # 通过一个中间空间连接到外部
                base_ach = np.mean(self.medium_ach_range)
            else:
                # 通过多个中间空间连接到外部
                base_ach = np.mean(self.low_ach_range)
            
            # 应用开口影响因子
            # 开口面积越大，通风率越高
            opening_area_factor = path["total_opening_area"] ** self.opening_influence
            
            # 应用路径衰减因子
            decay_factor = path["decay_factor"]
            
            # 计算此路径的贡献
            contribution = base_ach * opening_area_factor * decay_factor
            
            # 存储路径贡献
            path_contributions.append(contribution)
        
        # 计算总通风率（取路径贡献的加权平均）
        # 每个路径的权重与其阻力成反比
        weights = np.array([1.0 / (path["weight"] + 0.1) for path in paths])
        weights = weights / np.sum(weights)
        
        ach_rate = np.sum(np.array(path_contributions) * weights)
        
        # 确保通风率在合理范围内
        min_ach = self.low_ach_range[0]
        max_ach = self.high_ach
        
        # 限制在有效范围内
        ach_rate = max(min_ach, min(ach_rate, max_ach))
        
        return ach_rate
    
    def _validate_ach_rates(self, space_graph: nx.Graph) -> None:
        """
        验证通风率的物理合理性并调整
        
        Args:
            space_graph: 空间连接图
        """
        # 检查通风率的物理合理性
        # 例如，相邻空间的通风率不应该差异过大
        
        # 对每一对相邻空间
        for space1_id, space2_id in space_graph.edges():
            # 跳过外部节点
            if space1_id.startswith("space_exterior") or space2_id.startswith("space_exterior"):
                continue
                
            # 获取两个空间的通风率
            ach1 = self.ach_rates.get(space1_id, 0)
            ach2 = self.ach_rates.get(space2_id, 0)
            
            # 如果差异过大，调整
            if abs(ach1 - ach2) > 5.0:
                # 计算调整后的值（向平均值靠拢）
                average = (ach1 + ach2) / 2
                
                # 应用部分调整（避免过度修正）
                adjustment = 0.3  # 调整因子
                
                if ach1 > ach2:
                    self.ach_rates[space1_id] = ach1 - (ach1 - average) * adjustment
                    self.ach_rates[space2_id] = ach2 + (average - ach2) * adjustment
                else:
                    self.ach_rates[space1_id] = ach1 + (average - ach1) * adjustment
                    self.ach_rates[space2_id] = ach2 - (ach2 - average) * adjustment
    
    def calculate_ventilation_contributions(self, space_id: str) -> Dict[str, float]:
        """
        计算指定空间的通风路径贡献率
        
        Args:
            space_id: 空间ID
            
        Returns:
            路径贡献率字典，键为路径ID，值为贡献率
        """
        # 获取空间的通风路径
        paths = self.ventilation_paths.get(space_id, [])
        
        if not paths:
            return {}
        
        # 计算总权重（权重与阻力成反比）
        weights = [1.0 / (path["weight"] + 0.1) for path in paths]
        total_weight = sum(weights)
        
        # 计算每条路径的贡献率
        contributions = {}
        for i, path in enumerate(paths):
            contribution = weights[i] / total_weight if total_weight > 0 else 0
            path_id = f"path_{i+1}"
            contributions[path_id] = contribution
        
        return contributions
    
    def update_ach_for_opening_state(self, opening_states: Dict[str, str]) -> Dict[str, float]:
        """
        根据开口状态更新通风率
        
        Args:
            opening_states: 开口状态字典，键为开口ID，值为状态（open/closed）
            
        Returns:
            更新后的通风率字典
        """
        # 深度复制原始通风率
        updated_rates = self.ach_rates.copy()
        
        # 对每个空间
        for space_id, paths in self.ventilation_paths.items():
            # 检查每条通风路径
            path_affected = False
            
            for path in paths:
                # 检查路径上的每个开口
                for opening_id in path["via"]:
                    # 如果开口关闭，需要更新通风率
                    if opening_states.get(opening_id) == "closed":
                        path_affected = True
                        break
                
                if path_affected:
                    break
            
            # 如果有通风路径受影响，重新计算通风率
            if path_affected:
                # 简化处理：降低通风率
                # 实际系统中应该更精确地重新计算
                updated_rates[space_id] *= 0.7
        
        return updated_rates
    
    def get_ach_category(self, ach_rate: float) -> str:
        """
        根据通风率值返回分类
        
        Args:
            ach_rate: 通风率值（ACH）
            
        Returns:
            通风率分类（high/medium/low）
        """
        if ach_rate >= self.medium_ach_range[1]:
            return "high"
        elif ach_rate >= self.low_ach_range[1]:
            return "medium"
        else:
            return "low"


if __name__ == "__main__":
    # 测试通风率计算引擎
    calculator = AchCalculator()
    
    # 创建测试数据
    # 假设空间
    spaces = [
        {"id": "space_001", "volume": 100, "center": [5, 5, 3], "dimensions": [10, 10, 3], "type": "room"},
        {"id": "space_002", "volume": 80, "center": [15, 5, 3], "dimensions": [8, 10, 3], "type": "corridor"},
        {"id": "space_003", "volume": 120, "center": [5, 15, 3], "dimensions": [10, 10, 3], "type": "room"},
    ]
    
    # 创建测试图
    space_graph = nx.Graph()
    
    # 添加节点
    for space in spaces:
        space_graph.add_node(space["id"])
    
    # 添加外部节点
    space_graph.add_node("space_exterior")
    
    # 添加边
    space_graph.add_edge("space_001", "space_002", weight=1.0, openings=["opening_001"], opening_types=["door"])
    space_graph.add_edge("space_002", "space_003", weight=1.0, openings=["opening_002"], opening_types=["door"])
    space_graph.add_edge("space_001", "space_exterior", weight=0.5, openings=["opening_003"], opening_types=["window"])
    
    # 计算通风率
    result = calculator.calculate_ach_rates(spaces, space_graph, ["space_exterior"])
    
    print("通风率计算完成")
    for space_id, ach in calculator.ach_rates.items():
        category = calculator.get_ach_category(ach)
        print(f"{space_id} 通风率: {ach:.2f} ACH, 分类: {category}")
        
        # 打印通风路径
        paths = calculator.ventilation_paths.get(space_id, [])
        print(f"  通风路径数量: {len(paths)}")
        for i, path in enumerate(paths):
            print(f"  路径 {i+1}: {path['route']}, 权重: {path['weight']:.2f}, 衰减因子: {path['decay_factor']:.2f}")