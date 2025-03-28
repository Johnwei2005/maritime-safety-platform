"""
File: src/space_analysis/space_detector.py
空间分割与识别
识别并分割独立封闭空间，计算几何特性
"""

import os
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
from collections import deque
import networkx as nx
from scipy.ndimage import label, generate_binary_structure
from scipy.spatial import cKDTree

# 本地模块导入
from ..config import get_config
from ..utils.geometry_utils import find_connected_components, compute_boundingbox_features

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("space_detector")


class SpaceDetector:
    """空间分割与识别，负责从体素数据中识别独立空间"""
    
    def __init__(self):
        """初始化空间检测器"""
        self.config = get_config()
        
        # 获取空间识别参数
        self.min_space_volume = self.config.get("space_detection", "min_space_volume")
        self.space_merge_distance = self.config.get("space_detection", "space_merge_distance")
        self.min_passage_height = self.config.get("space_detection", "min_passage_height")
        self.max_seed_points = self.config.get("space_detection", "max_seed_points")
        self.flood_fill_step = self.config.get("space_detection", "flood_fill_step")
        
        # 存储检测到的空间
        self.spaces = []
        self.space_adjacency = nx.Graph()
        
        logger.info(f"初始化空间检测器，最小空间体积: {self.min_space_volume}m³，合并距离: {self.space_merge_distance}m")
    
    def detect_spaces(self, voxel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从体素数据中检测独立空间
        
        Args:
            voxel_data: 体素化数据，包含体素网格和相关信息
            
        Returns:
            空间检测结果字典
        """
        start_time = time.time()
        logger.info("开始空间检测")
        
        # 提取体素数据
        voxel_grid = voxel_data.get("voxel_grid")
        voxel_size_grid = voxel_data.get("voxel_size_grid", None)
        base_voxel_size = voxel_data.get("base_voxel_size")
        origin = voxel_data.get("origin")
        
        if voxel_grid is None:
            logger.error("无效的体素数据，缺少体素网格")
            return {"spaces": [], "adjacency": nx.Graph()}
        
        # 反转体素网格，获取空间体素
        empty_space = ~voxel_grid
        
        # 移除外部空间（洪水填充法）
        filled_spaces = self._remove_external_space(empty_space)
        
        # 识别连通区域（独立空间）
        logger.info("识别连通空间")
        
        # 使用3D连通区域标记
        # 6-连通：面连通，两个体素共面才连通
        # 18-连通：边连通，两个体素共边即连通
        # 26-连通：顶点连通，两个体素共顶点即连通
        connectivity = 6  # 使用面连通性
        spaces_components = find_connected_components(filled_spaces, connectivity)
        
        logger.info(f"检测到{len(spaces_components)}个潜在空间")
        
        # 过滤小空间，计算空间特征
        self.spaces = []
        valid_spaces_count = 0
        
        for i, component in enumerate(spaces_components):
            # 计算空间体积
            volume = len(component) * (base_voxel_size ** 3)
            
            # 过滤小于最小体积的空间
            if volume < self.min_space_volume:
                logger.debug(f"过滤小空间 #{i}，体积: {volume:.2f}m³")
                continue
            
            # 计算空间坐标
            voxel_coords = component
            real_coords = origin + (voxel_coords + 0.5) * base_voxel_size
            
            # 计算包围盒
            bbox_min = np.min(real_coords, axis=0)
            bbox_max = np.max(real_coords, axis=0)
            
            # 计算中心点
            center = np.mean(real_coords, axis=0)
            
            # 生成空间ID
            space_id = f"space_{valid_spaces_count:03d}"
            valid_spaces_count += 1
            
            # 创建空间对象
            space = {
                "id": space_id,
                "volume": volume,
                "center": center.tolist(),
                "bbox_min": bbox_min.tolist(),
                "bbox_max": bbox_max.tolist(),
                "dimensions": (bbox_max - bbox_min).tolist(),
                "voxel_count": len(component),
                "voxel_indices": component.tolist(),
                "type": "unknown",  # 类型将在后续分类中确定
            }
            
            self.spaces.append(space)
        
        logger.info(f"识别出{len(self.spaces)}个有效空间")
        
        # 检测空间间的邻接关系
        self._detect_space_adjacency(voxel_grid, base_voxel_size)
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"空间检测完成，耗时: {elapsed_time:.2f}秒")
        
        return {
            "spaces": self.spaces,
            "adjacency": self.space_adjacency,
            "elapsed_time": elapsed_time
        }
    
    def _remove_external_space(self, empty_space: np.ndarray) -> np.ndarray:
        """
        移除外部空间，保留封闭空间
        
        Args:
            empty_space: 表示空间的体素网格（True为空，False为实体）
            
        Returns:
            移除外部空间后的体素网格
        """
        logger.info("移除外部空间")
        
        # 复制数组，避免修改原始数据
        filled_spaces = empty_space.copy()
        
        # 从边界开始洪水填充
        # 创建与原数组相同形状，但全False的数组
        mask = np.zeros_like(empty_space, dtype=bool)
        
        # 边界点
        # x边界
        mask[0, :, :] = empty_space[0, :, :]
        mask[-1, :, :] = empty_space[-1, :, :]
        # y边界
        mask[:, 0, :] = empty_space[:, 0, :]
        mask[:, -1, :] = empty_space[:, -1, :]
        # z边界
        mask[:, :, 0] = empty_space[:, :, 0]
        mask[:, :, -1] = empty_space[:, :, -1]
        
        # 获取种子点
        seeds = np.argwhere(mask)
        
        # 如果种子点过多，进行采样
        if len(seeds) > self.max_seed_points:
            np.random.shuffle(seeds)
            seeds = seeds[:self.max_seed_points]
        
        # 从每个种子点进行洪水填充
        for seed in seeds:
            self._flood_fill_3d(filled_spaces, tuple(seed))
        
        # 反转结果，True表示内部空间
        return filled_spaces
    
    def _flood_fill_3d(self, grid: np.ndarray, start_point: Tuple[int, int, int]) -> None:
        """
        3D洪水填充算法
        
        Args:
            grid: 要填充的3D网格（True为空，False为实体），将直接修改
            start_point: 起始点坐标元组(x,y,z)
        """
        # 如果起始点不为空，不需要填充
        if not grid[start_point]:
            return
            
        # 获取网格尺寸
        shape = grid.shape
        
        # 创建队列，用于广度优先搜索
        queue = deque([start_point])
        
        # 6-连通邻居方向：上下左右前后
        neighbors = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1)
        ]
        
        # 广度优先搜索填充
        while queue:
            x, y, z = queue.popleft()
            
            # 如果当前点已经填充，跳过
            if not grid[x, y, z]:
                continue
                
            # 填充当前点
            grid[x, y, z] = False
            
            # 检查所有邻居
            for dx, dy, dz in neighbors:
                nx, ny, nz = x + dx, y + dy, z + dz
                
                # 检查边界
                if (0 <= nx < shape[0] and 0 <= ny < shape[1] and 0 <= nz < shape[2]
                        and grid[nx, ny, nz]):
                    queue.append((nx, ny, nz))
    
    def _detect_space_adjacency(self, voxel_grid: np.ndarray, voxel_size: float) -> None:
        """
        检测空间间的邻接关系
        
        Args:
            voxel_grid: 体素网格
            voxel_size: 体素大小
        """
        logger.info("检测空间邻接关系")
        
        # 创建空的邻接图
        self.space_adjacency = nx.Graph()
        
        # 为每个空间添加节点
        for space in self.spaces:
            self.space_adjacency.add_node(space["id"], **space)
        
        # 如果只有0或1个空间，无需检测邻接关系
        if len(self.spaces) <= 1:
            return
            
        # 创建空间索引，加速邻近空间查找
        space_centers = np.array([space["center"] for space in self.spaces])
        space_tree = cKDTree(space_centers)
        
        # 检测潜在相邻空间
        for i, space in enumerate(self.spaces):
            # 计算搜索半径（基于空间尺寸）
            max_dim = max(space["dimensions"])
            search_radius = max_dim + voxel_size * 2
            
            # 查找可能相邻的空间
            nearby_indices = space_tree.query_ball_point(space["center"], search_radius)
            
            # 移除自身
            if i in nearby_indices:
                nearby_indices.remove(i)
                
            # 检查每个潜在相邻空间
            for j in nearby_indices:
                other_space = self.spaces[j]
                
                # 检查两个空间是否实际相邻
                if self._check_spaces_adjacent(space, other_space, voxel_grid, voxel_size):
                    # 添加边，表示相邻关系
                    self.space_adjacency.add_edge(space["id"], other_space["id"])
        
        logger.info(f"检测到{self.space_adjacency.number_of_edges()}个空间邻接关系")
    
    def _check_spaces_adjacent(self, space1: Dict[str, Any], space2: Dict[str, Any], 
                              voxel_grid: np.ndarray, voxel_size: float) -> bool:
        """
        检查两个空间是否相邻
        
        Args:
            space1: 第一个空间
            space2: 第二个空间
            voxel_grid: 体素网格
            voxel_size: 体素大小
            
        Returns:
            如果两个空间相邻则为True
        """
        # 获取两个空间的体素索引
        voxels1 = np.array(space1["voxel_indices"])
        voxels2 = np.array(space2["voxel_indices"])
        
        # 检查是否有体素直接相邻
        # 为了效率，我们检查两组体素的欧几里得距离的最小值是否小于等于根2
        # 这表示两个体素是否至少共享一个面
        
        # 计算体素到体素的距离（使用KD树优化）
        tree1 = cKDTree(voxels1)
        tree2 = cKDTree(voxels2)
        
        # 计算两个集合间的最小距离
        # k=1表示每个点查询最近的1个点
        dist, _ = tree1.query(voxels2, k=1, workers=-1)
        min_dist = np.min(dist)
        
        # 判断最小距离是否表示相邻（欧几里得距离<= sqrt(2)）
        # 但由于计算精度问题，使用稍大的阈值
        return min_dist <= 1.5
    
    def merge_fragmented_spaces(self) -> None:
        """
        合并被家具等物体分隔的连续空间
        """
        logger.info("合并分割空间")
        
        # 如果空间数量太少，无需合并
        if len(self.spaces) <= 1:
            return
            
        # 存储需要合并的空间
        merge_pairs = []
        
        # 检查每对相邻空间
        for edge in self.space_adjacency.edges():
            space1_id, space2_id = edge
            
            # 获取空间对象
            space1 = next(s for s in self.spaces if s["id"] == space1_id)
            space2 = next(s for s in self.spaces if s["id"] == space2_id)
            
            # 计算空间间的距离
            # 这里使用简化方法：中心点距离减去各自的最大半径
            space1_center = np.array(space1["center"])
            space2_center = np.array(space2["center"])
            space1_max_radius = max(space1["dimensions"]) / 2
            space2_max_radius = max(space2["dimensions"]) / 2
            
            center_distance = np.linalg.norm(space2_center - space1_center)
            estimated_separation = center_distance - space1_max_radius - space2_max_radius
            
            # 如果空间间隔小于阈值，考虑合并
            if estimated_separation <= self.space_merge_distance:
                merge_pairs.append((space1_id, space2_id))
        
        # 根据合并对创建连通分量
        merge_graph = nx.Graph()
        merge_graph.add_edges_from(merge_pairs)
        
        # 获取连通分量（每个分量中的空间将被合并）
        components = list(nx.connected_components(merge_graph))
        
        # 如果没有需要合并的空间，返回
        if not components:
            return
            
        logger.info(f"将合并{len(components)}组分割空间")
        
        # 执行合并
        merged_spaces = []
        merged_space_ids = set()
        
        # 处理每个合并组
        for component in components:
            if len(component) <= 1:
                continue
                
            # 获取要合并的空间
            spaces_to_merge = [s for s in self.spaces if s["id"] in component]
            
            # 记录已合并的空间ID
            for space in spaces_to_merge:
                merged_space_ids.add(space["id"])
            
            # 合并空间
            merged_space = self._merge_spaces(spaces_to_merge)
            merged_spaces.append(merged_space)
        
        # 保留未合并的空间
        unmerged_spaces = [s for s in self.spaces if s["id"] not in merged_space_ids]
        
        # 更新空间列表
        self.spaces = unmerged_spaces + merged_spaces
        
        # 更新邻接图
        self._update_adjacency_after_merge()
        
        logger.info(f"空间合并后，总空间数量: {len(self.spaces)}")
    
    def _merge_spaces(self, spaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个空间为一个
        
        Args:
            spaces: 要合并的空间列表
            
        Returns:
            合并后的空间
        """
        # 生成新的ID
        new_id = f"space_merged_{uuid.uuid4().hex[:8]}"
        
        # 合并体素索引
        all_voxel_indices = []
        for space in spaces:
            all_voxel_indices.extend(space["voxel_indices"])
        
        # 转换为数组进行去重
        voxel_indices = np.unique(np.array(all_voxel_indices), axis=0)
        
        # 计算合并后的空间属性
        volume = sum(space["volume"] for space in spaces)
        voxel_count = len(voxel_indices)
        
        # 计算包围盒
        all_points = np.vstack([np.array(space["voxel_indices"]) for space in spaces])
        bbox_min = np.min(all_points, axis=0).tolist()
        bbox_max = np.max(all_points, axis=0).tolist()
        dimensions = [bbox_max[i] - bbox_min[i] for i in range(3)]
        
        # 计算中心点
        center = np.mean(all_points, axis=0).tolist()
        
        # 创建合并后的空间
        merged_space = {
            "id": new_id,
            "volume": volume,
            "center": center,
            "bbox_min": bbox_min,
            "bbox_max": bbox_max,
            "dimensions": dimensions,
            "voxel_count": voxel_count,
            "voxel_indices": voxel_indices.tolist(),
            "type": "merged",  # 标记为合并空间
            "merged_from": [space["id"] for space in spaces]  # 记录源空间
        }
        
        return merged_space
    
    def _update_adjacency_after_merge(self) -> None:
        """
        在空间合并后更新邻接图
        """
        # 创建新的邻接图
        new_adjacency = nx.Graph()
        
        # 为每个空间添加节点
        for space in self.spaces:
            new_adjacency.add_node(space["id"], **space)
        
        # 检测合并后的空间邻接关系
        for i, space1 in enumerate(self.spaces):
            for j, space2 in enumerate(self.spaces[i+1:], i+1):
                # 检查两个空间是否相邻
                
                # 如果是合并空间，检查源空间的关系
                if "merged_from" in space1 and "merged_from" in space2:
                    # 检查源空间是否有相邻关系
                    for src1 in space1["merged_from"]:
                        for src2 in space2["merged_from"]:
                            if self.space_adjacency.has_edge(src1, src2):
                                new_adjacency.add_edge(space1["id"], space2["id"])
                                break
                        else:
                            continue
                        break
                elif "merged_from" in space1:
                    # space1是合并空间，space2是未合并空间
                    for src in space1["merged_from"]:
                        if self.space_adjacency.has_edge(src, space2["id"]):
                            new_adjacency.add_edge(space1["id"], space2["id"])
                            break
                elif "merged_from" in space2:
                    # space2是合并空间，space1是未合并空间
                    for src in space2["merged_from"]:
                        if self.space_adjacency.has_edge(space1["id"], src):
                            new_adjacency.add_edge(space1["id"], space2["id"])
                            break
                else:
                    # 都是未合并空间，保持原有关系
                    if self.space_adjacency.has_edge(space1["id"], space2["id"]):
                        new_adjacency.add_edge(space1["id"], space2["id"])
        
        # 更新邻接图
        self.space_adjacency = new_adjacency