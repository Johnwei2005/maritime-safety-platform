"""
File: src/space_analysis/opening_detector.py
通道与门检测器
识别空间间的连接开口，区分通道（大开口）和门（小开口）
"""

import os
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
from collections import deque
import networkx as nx
from scipy.spatial import cKDTree, ConvexHull
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN

# 本地模块导入
from ..config import get_config
from ..utils.geometry_utils import compute_opening_features, compute_opening_direction

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opening_detector")


class OpeningDetector:
    """通道与门检测器，负责识别空间间的连接开口"""
    
    def __init__(self):
        """初始化开口检测器"""
        self.config = get_config()
        
        # 获取开口检测参数
        self.standard_door_area_limit = self.config.get("openings", "standard_door_area_limit")
        self.wide_door_area_limit = self.config.get("openings", "wide_door_area_limit")
        self.passage_aspect_ratio = self.config.get("openings", "passage_aspect_ratio")
        self.connection_degree_threshold = self.config.get("openings", "connection_degree_threshold")
        self.opening_height_range = self.config.get("openings", "opening_height_range")
        
        # 存储检测到的开口
        self.openings = []
        
        logger.info(f"初始化开口检测器，标准门面积上限: {self.standard_door_area_limit}m²，宽门面积上限: {self.wide_door_area_limit}m²")
    
    def detect_openings(self, voxel_data: Dict[str, Any], spaces: List[Dict[str, Any]], 
                       space_adjacency: nx.Graph) -> Dict[str, Any]:
        """
        检测空间间的开口（门和通道）
        
        Args:
            voxel_data: 体素数据
            spaces: 检测到的空间列表
            space_adjacency: 空间邻接图
            
        Returns:
            开口检测结果字典
        """
        start_time = time.time()
        logger.info("开始检测空间间的开口")
        
        # 重置开口列表
        self.openings = []
        
        # 提取体素数据
        voxel_grid = voxel_data.get("voxel_grid")
        base_voxel_size = voxel_data.get("base_voxel_size")
        origin = voxel_data.get("origin")
        
        if voxel_grid is None or not spaces:
            logger.error("无效的输入数据")
            return {"openings": []}
        
        # 检查每对相邻空间
        opening_id = 0
        
        for space1_id, space2_id in space_adjacency.edges():
            # 获取空间对象
            space1 = next(s for s in spaces if s["id"] == space1_id)
            space2 = next(s for s in spaces if s["id"] == space2_id)
            
            # 检测两个空间之间的开口
            openings = self._detect_openings_between_spaces(
                space1, space2, voxel_grid, base_voxel_size, origin
            )
            
            # 为开口分配ID并添加到列表
            for opening in openings:
                opening_id += 1
                opening["id"] = f"opening_{opening_id:03d}"
                opening["connects"] = [space1_id, space2_id]
                self.openings.append(opening)
        
        logger.info(f"共检测到{len(self.openings)}个开口")
        
        # 分类开口（门vs通道）
        self._classify_openings()
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"开口检测完成，耗时: {elapsed_time:.2f}秒")
        
        return {
            "openings": self.openings,
            "elapsed_time": elapsed_time
        }
    
    def _detect_openings_between_spaces(self, space1: Dict[str, Any], space2: Dict[str, Any],
                                      voxel_grid: np.ndarray, voxel_size: float,
                                      origin: np.ndarray) -> List[Dict[str, Any]]:
        """
        检测两个空间之间的开口
        
        Args:
            space1: 第一个空间
            space2: 第二个空间
            voxel_grid: 体素网格
            voxel_size: 体素大小
            origin: 体素网格原点
            
        Returns:
            开口列表
        """
        # 获取两个空间的体素索引
        voxels1 = np.array(space1["voxel_indices"])
        voxels2 = np.array(space2["voxel_indices"])
        
        # 寻找两个空间之间的界面
        interface_voxels = self._find_space_interface(voxels1, voxels2)
        
        if len(interface_voxels) == 0:
            return []
            
        # 将界面体素划分为不同的开口
        opening_clusters = self._cluster_interface_voxels(interface_voxels)
        
        # 为每个开口计算特征并创建对象
        openings = []
        
        for cluster in opening_clusters:
            # 计算开口的真实坐标
            points = origin + (cluster + 0.5) * voxel_size
            
            # 计算开口特征
            features = compute_opening_features(points)
            
            # 计算开口方向
            direction, planarity = compute_opening_direction(points)
            
            # 创建开口对象
            opening = {
                "id": "",  # 将在外部分配
                "type": "unknown",  # 将在后续分类
                "connects": [],  # 将在外部分配
                "position": np.mean(points, axis=0).tolist(),
                "voxel_indices": cluster.tolist(),
                "area": features["area"],
                "width": features["width"],
                "height": features["height"],
                "aspect_ratio": features["aspect_ratio"],
                "direction": direction.tolist(),
                "planarity": planarity,
                "points": points.tolist(),
                "state": "open"  # 默认状态
            }
            
            openings.append(opening)
        
        return openings
    
    def _find_space_interface(self, voxels1: np.ndarray, voxels2: np.ndarray) -> np.ndarray:
        """
        找到两个空间之间的界面体素
        
        Args:
            voxels1: 第一个空间的体素索引
            voxels2: 第二个空间的体素索引
            
        Returns:
            界面体素的索引
        """
        # 为两个空间的体素建立KD树
        tree1 = cKDTree(voxels1)
        tree2 = cKDTree(voxels2)
        
        # 找到最近邻是对方空间且距离为1的体素（共面）
        neighbors1 = []
        for voxel in voxels1:
            distance, idx = tree2.query(voxel, k=1)
            if distance == 1:  # 距离为1表示两个体素共面
                neighbors1.append(voxel)
        
        neighbors2 = []
        for voxel in voxels2:
            distance, idx = tree1.query(voxel, k=1)
            if distance == 1:
                neighbors2.append(voxel)
        
        # 合并两侧的界面体素
        if len(neighbors1) > 0 and len(neighbors2) > 0:
            interface_voxels = np.vstack([neighbors1, neighbors2])
        elif len(neighbors1) > 0:
            interface_voxels = np.array(neighbors1)
        elif len(neighbors2) > 0:
            interface_voxels = np.array(neighbors2)
        else:
            interface_voxels = np.array([])
        
        return interface_voxels
    
    def _cluster_interface_voxels(self, interface_voxels: np.ndarray) -> List[np.ndarray]:
        """
        将界面体素聚类为不同的开口
        
        Args:
            interface_voxels: 界面体素的索引
            
        Returns:
            开口聚类列表
        """
        if len(interface_voxels) == 0:
            return []
            
        # 使用DBSCAN进行聚类
        # eps参数表示两个点被视为邻居的最大距离
        # min_samples表示构成核心点的最小邻居数
        clustering = DBSCAN(eps=1.5, min_samples=2).fit(interface_voxels)
        
        # 获取聚类标签
        labels = clustering.labels_
        
        # 组织聚类结果
        clusters = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            # 忽略噪声点（标签为-1）
            if label == -1:
                continue
                
            # 获取当前聚类的点
            cluster_points = interface_voxels[labels == label]
            
            # 只保留足够大的开口（至少3个体素）
            if len(cluster_points) >= 3:
                clusters.append(cluster_points)
        
        return clusters
    
    def _classify_openings(self) -> None:
        """
        对检测到的开口进行分类（门vs通道）
        """
        for opening in self.openings:
            # 根据面积和纵横比分类
            area = opening["area"]
            width = opening["width"]
            aspect_ratio = opening["aspect_ratio"]
            
            # 分类逻辑
            if area <= self.standard_door_area_limit and aspect_ratio >= 1.5:
                # 小面积高窄的开口是标准门
                opening["type"] = "standard_door"
            elif area <= self.wide_door_area_limit and width < 3.0:
                # 中等面积但不太宽的开口是宽门/双开门
                opening["type"] = "wide_door"
            elif area > self.wide_door_area_limit or aspect_ratio >= self.passage_aspect_ratio:
                # 大面积或细长的开口是通道
                opening["type"] = "passage"
            else:
                # 其他情况默认为标准门
                opening["type"] = "standard_door"
    
    def detect_door_states(self, voxel_data: Dict[str, Any]) -> None:
        """
        检测门的状态（开/关）
        
        Args:
            voxel_data: 体素数据
        """
        # 此方法在原型系统中简化处理
        # 实际系统中可能需要分析门区域的体素占用情况
        
        # 提取体素数据
        voxel_grid = voxel_data.get("voxel_grid")
        if voxel_grid is None:
            return
            
        # 默认所有门都是开的
        for opening in self.openings:
            if "door" in opening["type"]:
                opening["state"] = "open"
    
    def extract_opening_features(self, opening: Dict[str, Any]) -> Dict[str, float]:
        """
        提取开口的特征向量，用于更精确的分类
        
        Args:
            opening: 开口对象
            
        Returns:
            特征字典
        """
        # 提取17种几何特征
        features = {}
        
        # 基本几何特征
        features["area"] = opening["area"]
        features["width"] = opening["width"]
        features["height"] = opening["height"]
        features["aspect_ratio"] = opening["aspect_ratio"]
        features["planarity"] = opening["planarity"]
        
        # 计算开口点的分布特征
        points = np.array(opening["points"])
        if len(points) >= 3:
            # 计算点云的协方差矩阵的特征值
            pca = PCA(n_components=3)
            pca.fit(points)
            
            # 特征值表示点分布的主要方向上的方差
            eigenvalues = pca.explained_variance_
            
            features["eigenvalue_1"] = eigenvalues[0]
            features["eigenvalue_2"] = eigenvalues[1]
            features["eigenvalue_3"] = eigenvalues[2]
            
            # 计算几何形状特征
            # 线性度、平面度、球度
            sum_eigenvalues = np.sum(eigenvalues)
            if sum_eigenvalues > 0:
                features["linearity"] = (eigenvalues[0] - eigenvalues[1]) / sum_eigenvalues
                features["planarity"] = (eigenvalues[1] - eigenvalues[2]) / sum_eigenvalues
                features["sphericity"] = eigenvalues[2] / sum_eigenvalues
            
            # 计算点云边界框
            min_point = np.min(points, axis=0)
            max_point = np.max(points, axis=0)
            bbox_dims = max_point - min_point
            
            features["bbox_volume"] = np.prod(bbox_dims)
            features["bbox_area_xy"] = bbox_dims[0] * bbox_dims[1]
            features["bbox_area_xz"] = bbox_dims[0] * bbox_dims[2]
            features["bbox_area_yz"] = bbox_dims[1] * bbox_dims[2]
            
            # 计算点云的凸包体积（3D情况下）
            try:
                hull = ConvexHull(points)
                features["convex_hull_volume"] = hull.volume
                features["convex_hull_area"] = hull.area
            except Exception:
                features["convex_hull_volume"] = 0
                features["convex_hull_area"] = 0
        
        return features
    
    def get_openings_for_space(self, space_id: str) -> List[Dict[str, Any]]:
        """
        获取与指定空间相连的所有开口
        
        Args:
            space_id: 空间ID
            
        Returns:
            与该空间相连的开口列表
        """
        return [
            opening for opening in self.openings
            if space_id in opening["connects"]
        ]
    
    def get_connectivity_graph(self) -> nx.Graph:
        """
        创建通过开口连接的空间连通性图
        
        Returns:
            空间连通性图
        """
        graph = nx.Graph()
        
        # 添加边，表示空间之间的连接
        for opening in self.openings:
            space1_id, space2_id = opening["connects"]
            
            # 如果边已存在，更新属性
            if graph.has_edge(space1_id, space2_id):
                # 获取现有的开口列表
                edge_data = graph.get_edge_data(space1_id, space2_id)
                openings = edge_data.get("openings", [])
                openings.append(opening["id"])
                
                # 更新边属性
                graph[space1_id][space2_id]["openings"] = openings
                graph[space1_id][space2_id]["count"] = len(openings)
            else:
                # 创建新边
                graph.add_edge(
                    space1_id, space2_id,
                    openings=[opening["id"]],
                    count=1,
                    type=opening["type"]
                )
        
        return graph


if __name__ == "__main__":
    # 测试开口检测器
    detector = OpeningDetector()
    
    # 创建测试数据
    # 这里需要实际的空间和体素数据进行测试
    # 以下是简化的测试代码框架
    voxel_data = {
        "voxel_grid": np.ones((20, 20, 10), dtype=bool),
        "base_voxel_size": 1.0,
        "origin": np.array([0, 0, 0])
    }
    
    # 创建两个假设的空间
    space1 = {
        "id": "space_001",
        "voxel_indices": [[i, j, k] for i in range(3, 8) for j in range(3, 8) for k in range(3, 8)]
    }
    
    space2 = {
        "id": "space_002",
        "voxel_indices": [[i, j, k] for i in range(9, 14) for j in range(3, 8) for k in range(3, 8)]
    }
    
    # 创建空间邻接图
    adjacency = nx.Graph()
    adjacency.add_edge("space_001", "space_002")
    
    # 检测开口
    result = detector.detect_openings(voxel_data, [space1, space2], adjacency)
    
    print(f"检测到{len(result['openings'])}个开口")
    for opening in result['openings']:
        print(f"开口ID: {opening['id']}, 类型: {opening['type']}, 连接: {opening['connects']}")