#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: src/ventilation/topology_builder.py
拓扑网络构建器
创建空间连接图，记录连接属性，计算拓扑特性
"""

import os
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
import networkx as nx
from networkx.algorithms.centrality import betweenness_centrality, closeness_centrality
from networkx.algorithms.shortest_paths.generic import shortest_path, all_shortest_paths
from networkx.algorithms.shortest_paths.weighted import dijkstra_path

# 本地模块导入
from ..config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("topology_builder")


class TopologyBuilder:
    """拓扑网络构建器，创建空间连接图并分析连通性"""
    
    def __init__(self):
        """初始化拓扑网络构建器"""
        self.config = get_config()
        
        # 内部存储
        self.space_graph = None  # 空间连接图
        self.exterior_nodes = set()  # 外部空间节点
        self.space_properties = {}  # 空间属性字典
        
        logger.info("初始化拓扑网络构建器")
    
    def build_topology(self, spaces: List[Dict[str, Any]], openings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建空间连接拓扑网络
        
        Args:
            spaces: 空间列表
            openings: 开口列表
            
        Returns:
            拓扑分析结果字典
        """
        start_time = time.time()
        logger.info("开始构建空间拓扑网络")
        
        # 创建初始图
        self.space_graph = nx.Graph()
        
        # 添加空间节点
        for space in spaces:
            self.space_graph.add_node(
                space["id"],
                type="space",
                volume=space.get("volume", 0),
                center=space.get("center", [0, 0, 0]),
                dimensions=space.get("dimensions", [0, 0, 0]),
                space_type=space.get("type", "unknown")
            )
            
            # 存储空间属性
            self.space_properties[space["id"]] = space
        
        # 添加外部空间节点
        exterior_id = "space_exterior"
        self.space_graph.add_node(
            exterior_id,
            type="exterior",
            volume=float('inf'),
            center=[0, 0, 0],
            dimensions=[0, 0, 0],
            space_type="exterior"
        )
        self.exterior_nodes.add(exterior_id)
        
        # 添加开口连接边
        for opening in openings:
            # 获取连接的空间
            connected_spaces = opening.get("connects", [])
            
            # 如果只连接一个空间，可能是连接到外部
            if len(connected_spaces) == 1:
                connected_spaces.append(exterior_id)
            
            # 跳过无效连接
            if len(connected_spaces) != 2:
                continue
                
            # 提取空间ID
            space1_id, space2_id = connected_spaces
            
            # 检查空间是否存在
            if not (self.space_graph.has_node(space1_id) and self.space_graph.has_node(space2_id)):
                continue
            
            # 计算开口权重（基于面积）
            weight = 1.0
            if "area" in opening:
                # 面积越大，阻力越小
                area = opening["area"]
                # 避免除零
                if area > 0:
                    weight = 1.0 / area
                else:
                    weight = 10.0  # 默认高阻力
            
            # 如果边已存在，更新属性
            if self.space_graph.has_edge(space1_id, space2_id):
                # 获取现有的开口列表和权重
                edge_data = self.space_graph.get_edge_data(space1_id, space2_id)
                openings_list = edge_data.get("openings", [])
                current_weight = edge_data.get("weight", 1.0)
                
                # 更新开口列表
                openings_list.append(opening["id"])
                
                # 更新权重（选择最小阻力，即最大通风能力）
                new_weight = min(current_weight, weight)
                
                # 更新边属性
                self.space_graph[space1_id][space2_id].update({
                    "openings": openings_list,
                    "count": len(openings_list),
                    "weight": new_weight,
                    "opening_types": edge_data.get("opening_types", []) + [opening["type"]]
                })
            else:
                # 创建新边
                self.space_graph.add_edge(
                    space1_id, space2_id,
                    openings=[opening["id"]],
                    count=1,
                    weight=weight,
                    opening_types=[opening["type"]]
                )
        
        # 计算拓扑特性
        self._calculate_topology_properties()
        
        # 验证拓扑连通性
        self._validate_topology()
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"空间拓扑网络构建完成，耗时: {elapsed_time:.2f}秒")
        
        return {
            "space_graph": self.space_graph,
            "exterior_nodes": list(self.exterior_nodes),
            "isolated_spaces": self._find_isolated_spaces(),
            "elapsed_time": elapsed_time
        }
    
    def _calculate_topology_properties(self) -> None:
        """计算拓扑特性（中心性、连通性等）"""
        logger.info("计算拓扑特性")
        
        # 计算节点中心性指标
        # 介数中心性：衡量节点在网络中的"桥梁"作用
        betweenness = betweenness_centrality(self.space_graph, weight='weight')
        
        # 接近中心性：衡量节点到所有其他节点的平均最短路径长度的倒数
        closeness = closeness_centrality(self.space_graph, distance='weight')
        
        # 度中心性：节点的连接数
        degree = dict(self.space_graph.degree())
        
        # 将结果存储为节点属性
        for node in self.space_graph.nodes():
            self.space_graph.nodes[node]['betweenness'] = betweenness.get(node, 0)
            self.space_graph.nodes[node]['closeness'] = closeness.get(node, 0)
            self.space_graph.nodes[node]['degree'] = degree.get(node, 0)
            
            # 计算中心性评分（综合多个指标）
            centrality_score = (
                0.4 * betweenness.get(node, 0) / max(betweenness.values(), default=1) +
                0.4 * closeness.get(node, 0) / max(closeness.values(), default=1) +
                0.2 * degree.get(node, 0) / max(degree.values(), default=1)
            )
            self.space_graph.nodes[node]['centrality_score'] = centrality_score
    
    def _validate_topology(self) -> None:
        """验证拓扑一致性，修复识别错误"""
        logger.info("验证拓扑一致性")
        
        # 检查连通性
        components = list(nx.connected_components(self.space_graph))
        
        # 如果有多个连通分量，可能需要修复
        if len(components) > 1:
            logger.warning(f"检测到{len(components)}个独立的空间组，可能存在连通性问题")
            
            # 找出包含外部节点的组件
            exterior_component = None
            for component in components:
                if any(node in self.exterior_nodes for node in component):
                    exterior_component = component
                    break
            
            # 如果找到外部组件，尝试连接其他组件到外部
            if exterior_component:
                # 将其他组件中最大的空间连接到外部
                for component in components:
                    if component != exterior_component:
                        # 找出组件中最大的空间
                        largest_space = None
                        max_volume = 0
                        for node in component:
                            if node in self.space_properties:
                                volume = self.space_properties[node].get("volume", 0)
                                if volume > max_volume:
                                    max_volume = volume
                                    largest_space = node
                        
                        # 连接到外部
                        if largest_space:
                            exterior_id = next(iter(self.exterior_nodes), None)
                            if exterior_id:
                                logger.warning(f"添加修复连接: {largest_space} -> {exterior_id}")
                                self.space_graph.add_edge(
                                    largest_space, exterior_id,
                                    openings=["repair_opening"],
                                    count=1,
                                    weight=2.0,
                                    opening_types=["repair"],
                                    is_repair=True
                                )
    
    def _find_isolated_spaces(self) -> List[str]:
        """
        找出孤立空间（没有连接到外部）
        
        Returns:
            孤立空间ID列表
        """
        isolated_spaces = []
        
        # 检查每个空间节点
        for node in self.space_graph.nodes():
            # 跳过外部节点
            if node in self.exterior_nodes:
                continue
                
            # 检查是否可以到达外部节点
            can_reach_exterior = False
            for exterior_id in self.exterior_nodes:
                if nx.has_path(self.space_graph, node, exterior_id):
                    can_reach_exterior = True
                    break
            
            # 如果不能到达外部，标记为孤立
            if not can_reach_exterior:
                isolated_spaces.append(node)
        
        return isolated_spaces
    
    def find_path_to_exterior(self, space_id: str, max_paths: int = 3) -> List[Dict[str, Any]]:
        """
        找到从指定空间到外部的路径
        
        Args:
            space_id: 起始空间ID
            max_paths: 最大路径数量
            
        Returns:
            路径列表，每个路径是一个字典，包含路径信息
        """
        paths = []
        
        # 检查空间是否存在
        if space_id not in self.space_graph:
            logger.warning(f"空间不存在: {space_id}")
            return paths
        
        # 检查每个外部节点
        for exterior_id in self.exterior_nodes:
            # 检查是否存在路径
            if not nx.has_path(self.space_graph, space_id, exterior_id):
                continue
                
            try:
                # 尝试找到多条路径
                all_paths = list(all_shortest_paths(self.space_graph, space_id, exterior_id, weight='weight'))
                
                # 限制路径数量
                for i, path in enumerate(all_paths[:max_paths]):
                    # 计算路径权重
                    total_weight = 0
                    openings = []
                    
                    # 遍历路径上的每条边
                    for j in range(len(path) - 1):
                        u, v = path[j], path[j+1]
                        edge_data = self.space_graph.get_edge_data(u, v)
                        total_weight += edge_data.get("weight", 1.0)
                        edge_openings = edge_data.get("openings", [])
                        openings.extend(edge_openings)
                    
                    # 创建路径对象
                    path_obj = {
                        "route": path,
                        "via": openings,
                        "weight": total_weight,
                        "length": len(path) - 1,
                        "exterior": exterior_id
                    }
                    
                    paths.append(path_obj)
            except nx.NetworkXNoPath:
                # 没有找到路径
                pass
        
        # 按权重排序路径（权重较小的在前）
        paths.sort(key=lambda x: x["weight"])
        
        return paths
    
    def calculate_space_connectivity(self) -> Dict[str, Dict[str, float]]:
        """
        计算每个空间的连通性指标
        
        Returns:
            空间连通性指标字典
        """
        result = {}
        
        # 对每个空间节点
        for node in self.space_graph.nodes():
            # 跳过外部节点
            if node in self.exterior_nodes:
                continue
                
            # 计算到外部的路径
            exterior_paths = self.find_path_to_exterior(node)
            
            # 计算连通性指标
            if exterior_paths:
                # 最短路径的权重
                min_weight = exterior_paths[0]["weight"]
                
                # 到外部的平均层数
                avg_layers = sum(p["length"] for p in exterior_paths) / len(exterior_paths)
                
                # 可用路径数量
                num_paths = len(exterior_paths)
                
                # 汇总指标
                connectivity = {
                    "min_weight": min_weight,
                    "avg_layers": avg_layers,
                    "num_paths": num_paths,
                    "has_path_to_exterior": True,
                    "paths": exterior_paths
                }
            else:
                connectivity = {
                    "min_weight": float('inf'),
                    "avg_layers": float('inf'),
                    "num_paths": 0,
                    "has_path_to_exterior": False,
                    "paths": []
                }
                
            result[node] = connectivity
        
        return result
    
    def identify_critical_connections(self) -> List[Tuple[str, str]]:
        """
        识别关键连接（删除后会增加系统脆弱性的连接）
        
        Returns:
            关键连接列表（边的元组）
        """
        # 计算边介数中心性
        edge_betweenness = nx.edge_betweenness_centrality(self.space_graph, weight='weight')
        
        # 获取关键连接（中心性较高的边）
        # 按中心性降序排序
        sorted_edges = sorted(edge_betweenness.keys(), key=lambda e: edge_betweenness[e], reverse=True)
        
        # 提取排名靠前的边
        num_critical = min(10, len(sorted_edges))
        critical_edges = sorted_edges[:num_critical]
        
        return critical_edges
    
    def find_important_spaces(self) -> List[str]:
        """
        找出重要空间（具有高中心性的空间）
        
        Returns:
            重要空间ID列表
        """
        # 创建中心性评分字典
        scores = {}
        for node in self.space_graph.nodes():
            if node not in self.exterior_nodes:
                scores[node] = self.space_graph.nodes[node].get('centrality_score', 0)
        
        # 按中心性评分排序
        sorted_spaces = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
        
        # 提取排名靠前的空间
        num_important = min(5, len(sorted_spaces))
        important_spaces = sorted_spaces[:num_important]
        
        return important_spaces
    
    def evaluate_topology_resilience(self) -> Dict[str, Any]:
        """
        评估拓扑网络的韧性
        
        Returns:
            拓扑韧性评估结果
        """
        # 计算图的关键指标
        
        # 平均路径长度
        try:
            avg_path_length = nx.average_shortest_path_length(self.space_graph, weight='weight')
        except nx.NetworkXError:
            # 图不连通
            avg_path_length = float('inf')
        
        # 聚类系数
        clustering = nx.average_clustering(self.space_graph)
        
        # 直径
        try:
            diameter = nx.diameter(self.space_graph, weight='weight')
        except nx.NetworkXError:
            diameter = float('inf')
        
        # 找出关键连接
        critical_connections = self.identify_critical_connections()
        
        # 计算连通性韧性（删除一条边后的连通性变化）
        resilience = 0
        original_components = nx.number_connected_components(self.space_graph)
        
        for edge in critical_connections[:3]:  # 只测试前三个关键连接
            # 临时删除边
            self.space_graph.remove_edge(*edge)
            
            # 计算变化
            new_components = nx.number_connected_components(self.space_graph)
            change = new_components - original_components
            resilience += change
            
            # 恢复边
            u, v = edge
            # 需要恢复原始属性
            edge_data = self.space_graph.get_edge_data(u, v, default={})
            self.space_graph.add_edge(u, v, **edge_data)
        
        # 结果
        return {
            "avg_path_length": avg_path_length,
            "clustering": clustering,
            "diameter": diameter,
            "resilience_score": 1.0 / (1.0 + resilience),  # 归一化
            "critical_connections": critical_connections
        }
    
    def get_opening_status_graph(self, opening_states: Dict[str, str]) -> nx.Graph:
        """
        根据开口状态创建当前状态下的图
        
        Args:
            opening_states: 开口状态字典，键为开口ID，值为状态（open/closed）
            
        Returns:
            考虑开口状态的图
        """
        # 创建图的副本
        status_graph = self.space_graph.copy()
        
        # 更新边的权重，关闭的开口对应的边权重增加
        for u, v, data in status_graph.edges(data=True):
            openings = data.get("openings", [])
            
            # 检查每个开口的状态
            for opening_id in openings:
                # 如果开口关闭，增加权重
                if opening_states.get(opening_id) == "closed":
                    # 显著增加权重
                    status_graph[u][v]["weight"] *= 10
        
        return status_graph


if __name__ == "__main__":
    # 测试拓扑网络构建器
    builder = TopologyBuilder()
    
    # 创建测试数据
    # 假设空间
    spaces = [
        {"id": "space_001", "volume": 100, "center": [5, 5, 3], "dimensions": [10, 10, 3], "type": "room"},
        {"id": "space_002", "volume": 80, "center": [15, 5, 3], "dimensions": [8, 10, 3], "type": "corridor"},
        {"id": "space_003", "volume": 120, "center": [5, 15, 3], "dimensions": [10, 10, 3], "type": "room"},
    ]
    
    # 假设开口
    openings = [
        {"id": "opening_001", "connects": ["space_001", "space_002"], "area": 2.0, "type": "door"},
        {"id": "opening_002", "connects": ["space_002", "space_003"], "area": 1.5, "type": "door"},
        {"id": "opening_003", "connects": ["space_001"], "area": 3.0, "type": "window"},  # 连接到外部
    ]
    
    # 构建拓扑
    result = builder.build_topology(spaces, openings)
    
    print("拓扑网络构建完成")
    print(f"节点数: {builder.space_graph.number_of_nodes()}")
    print(f"边数: {builder.space_graph.number_of_edges()}")
    print(f"孤立空间: {result['isolated_spaces']}")
    
    # 测试路径搜索
    paths = builder.find_path_to_exterior("space_001")
    print(f"空间1到外部的路径: {len(paths)}")
    for path in paths:
        print(f"  路径: {path['route']}, 权重: {path['weight']}")
    
    # 计算连通性
    connectivity = builder.calculate_space_connectivity()
    for space_id, conn in connectivity.items():
        print(f"{space_id}的连通性: 到外部路径数={conn['num_paths']}, 平均层数={conn['avg_layers']:.2f}")