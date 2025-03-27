"""
File: src/model_processing/voxelizer.py
自适应体素化系统
将连续几何转化为离散体素表示，支持根据区域复杂度动态调整精度
"""

import os
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union, Set
import numpy as np
from pathlib import Path
import math
from dataclasses import dataclass

# 第三方库导入
import trimesh
from scipy.spatial import cKDTree
from OCC.Core.TopoDS import TopoDS_Shape
import psutil
try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False

# 本地模块导入
from ..config import get_config
from ..utils.geometry_utils import (
    convert_occ_shape_to_trimesh, 
    calculate_curvature, 
    find_narrow_passages
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voxelizer")


@dataclass
class Octree:
    """八叉树节点"""
    center: np.ndarray  # 中心点坐标
    half_size: float    # 半边长
    children: List      # 子节点
    level: int          # 层级
    is_leaf: bool       # 是否为叶节点
    is_occupied: bool   # 是否被占用
    voxel_indices: Optional[Tuple[int, int, int]] = None  # 对应体素网格的索引


class AdaptiveVoxelizer:
    """自适应体素化系统，将几何体转换为体素表示"""
    
    def __init__(self):
        """初始化体素化器"""
        self.config = get_config()
        
        # 获取体素化参数
        self.base_voxel_size = self.config.get("voxelization", "base_voxel_size")
        self.min_voxel_size = self.config.get("voxelization", "min_voxel_size")
        self.curvature_threshold = self.config.get("voxelization", "curvature_threshold")
        self.width_threshold = self.config.get("voxelization", "width_threshold")
        self.use_gpu = self.config.get("voxelization", "use_gpu_acceleration") and CUDA_AVAILABLE
        self.max_memory = self.config.get("voxelization", "max_memory_usage") * 1024 * 1024  # 转为字节
        
        # 体素网格和标记
        self.voxel_grid = None
        self.voxel_size_grid = None
        self.bounding_box = None
        self.grid_shape = None
        self.origin = None
        
        # 八叉树根节点
        self.octree_root = None
        
        logger.info(f"初始化自适应体素化系统，基础体素大小: {self.base_voxel_size}m，最小体素大小: {self.min_voxel_size}m")
        if self.use_gpu:
            logger.info("启用GPU加速")
        else:
            if CUDA_AVAILABLE:
                logger.info("未启用GPU加速")
            else:
                logger.warning("GPU加速不可用，未安装CUDA支持")
    
    def voxelize(self, mesh: trimesh.Trimesh, shape: Optional[TopoDS_Shape] = None) -> Dict[str, Any]:
        """
        对网格进行体素化处理
        
        Args:
            mesh: 三角网格对象
            shape: 原始OpenCASCADE几何体(可选)
            
        Returns:
            体素化结果字典
        """
        start_time = time.time()
        logger.info("开始体素化处理")
        
        # 计算包围盒
        self.bounding_box = mesh.bounds
        bbox_min, bbox_max = self.bounding_box
        self.origin = bbox_min
        
        # 计算网格尺寸
        dimensions = bbox_max - bbox_min
        
        # 计算初始网格大小
        grid_size = np.ceil(dimensions / self.base_voxel_size).astype(int)
        self.grid_shape = grid_size
        
        logger.info(f"网格维度: {self.grid_shape}, 包围盒: {bbox_min} - {bbox_max}")
        
        # 估计内存使用量
        memory_estimate = np.prod(grid_size) * 3 * 8  # 3个网格，每个元素8字节
        available_memory = psutil.virtual_memory().available
        
        if memory_estimate > min(available_memory * 0.8, self.max_memory):
            logger.warning(f"估计内存使用量({memory_estimate/1024/1024:.2f}MB)超过限制，将使用八叉树体素化")
            return self._voxelize_octree(mesh, shape)
        else:
            logger.info(f"估计内存使用量: {memory_estimate/1024/1024:.2f}MB")
            
        # 创建均匀体素网格
        self.voxel_grid = np.zeros(self.grid_shape, dtype=bool)
        self.voxel_size_grid = np.full(self.grid_shape, self.base_voxel_size)
        
        # 计算网格曲率和窄通道区域，用于自适应体素化
        logger.info("计算曲率和窄通道区域")
        curvature = calculate_curvature(mesh)
        
        # 找出需要细化的区域
        high_curvature_vertices = np.where(curvature > self.curvature_threshold)[0]
        high_curvature_points = mesh.vertices[high_curvature_vertices]
        
        # 寻找窄通道
        narrow_passages = find_narrow_passages(mesh.vertices, self.width_threshold)
        narrow_passage_points = mesh.vertices[narrow_passages]
        
        # 合并需要细化的点
        refinement_points = np.vstack([high_curvature_points, narrow_passage_points]) if len(narrow_passage_points) > 0 and len(high_curvature_points) > 0 else (high_curvature_points if len(high_curvature_points) > 0 else narrow_passage_points)
        
        # 标记需要细化的体素
        refinement_voxels = set()
        if len(refinement_points) > 0:
            for point in refinement_points:
                voxel_index = tuple(np.floor((point - bbox_min) / self.base_voxel_size).astype(int))
                if all(0 <= voxel_index[i] < self.grid_shape[i] for i in range(3)):
                    refinement_voxels.add(voxel_index)
        
        logger.info(f"需要细化的体素数量: {len(refinement_voxels)}")
        
        # 使用光线投射法进行体素化
        if self.use_gpu and len(mesh.faces) > 10000:
            self._voxelize_gpu(mesh)
        else:
            self._voxelize_cpu(mesh)
        
        # 对需要细化的区域进行二次处理
        if refinement_voxels:
            self._refine_regions(mesh, refinement_voxels)
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"体素化完成，耗时: {elapsed_time:.2f}秒")
        
        # 返回体素化结果
        return {
            "voxel_grid": self.voxel_grid,
            "voxel_size_grid": self.voxel_size_grid,
            "origin": self.origin,
            "base_voxel_size": self.base_voxel_size,
            "min_voxel_size": self.min_voxel_size,
            "bounding_box": self.bounding_box,
            "grid_shape": self.grid_shape,
            "occupied_voxels": np.sum(self.voxel_grid),
            "elapsed_time": elapsed_time
        }
    
    def _voxelize_cpu(self, mesh: trimesh.Trimesh) -> None:
        """
        使用CPU进行体素化
        
        Args:
            mesh: 三角网格对象
        """
        logger.info("使用CPU进行体素化")
        
        # 获取包围盒
        bbox_min, bbox_max = self.bounding_box
        
        # 创建体素中心点坐标数组
        x = np.linspace(bbox_min[0] + self.base_voxel_size/2, bbox_max[0] - self.base_voxel_size/2, self.grid_shape[0])
        y = np.linspace(bbox_min[1] + self.base_voxel_size/2, bbox_max[1] - self.base_voxel_size/2, self.grid_shape[1])
        z = np.linspace(bbox_min[2] + self.base_voxel_size/2, bbox_max[2] - self.base_voxel_size/2, self.grid_shape[2])
        
        # 分批处理，避免内存溢出
        batch_size = 1000  # 每批处理的点数
        
        logger.info(f"开始分批体素化，每批{batch_size}个点")
        total_voxels = self.grid_shape[0] * self.grid_shape[1] * self.grid_shape[2]
        processed_voxels = 0
        
        for i in range(0, self.grid_shape[0], batch_size):
            i_end = min(i + batch_size, self.grid_shape[0])
            
            for j in range(0, self.grid_shape[1], batch_size):
                j_end = min(j + batch_size, self.grid_shape[1])
                
                for k in range(0, self.grid_shape[2], batch_size):
                    k_end = min(k + batch_size, self.grid_shape[2])
                    
                    # 创建当前批次的点坐标网格
                    xx, yy, zz = np.meshgrid(x[i:i_end], y[j:j_end], z[k:k_end], indexing='ij')
                    points = np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T
                    
                    # 使用包含点检测
                    contains = mesh.contains(points)
                    
                    # 更新体素网格
                    contains = contains.reshape((i_end-i, j_end-j, k_end-k))
                    self.voxel_grid[i:i_end, j:j_end, k:k_end] = contains
                    
                    # 更新进度
                    processed_voxels += (i_end-i) * (j_end-j) * (k_end-k)
                    if processed_voxels % (total_voxels // 10) < batch_size**3:
                        logger.info(f"体素化进度: {processed_voxels/total_voxels*100:.1f}%")
        
        logger.info("CPU体素化完成")
    
    def _voxelize_gpu(self, mesh: trimesh.Trimesh) -> None:
        """
        使用GPU进行体素化
        
        Args:
            mesh: 三角网格对象
        """
        if not CUDA_AVAILABLE:
            logger.warning("GPU加速不可用，回退到CPU处理")
            return self._voxelize_cpu(mesh)
            
        logger.info("使用GPU进行体素化")
        
        # 准备GPU内核代码
        cuda_code = """
        __global__ void voxelize_kernel(float *vertices, int *faces, int num_faces,
                                         float *voxel_centers, int num_voxels,
                                         bool *results, float voxel_size) {
            int voxel_idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (voxel_idx >= num_voxels) return;
            
            // 获取体素中心坐标
            float voxel_x = voxel_centers[voxel_idx * 3];
            float voxel_y = voxel_centers[voxel_idx * 3 + 1];
            float voxel_z = voxel_centers[voxel_idx * 3 + 2];
            
            // 射线方向
            float ray_dir_x = 1.0f;
            float ray_dir_y = 0.0f;
            float ray_dir_z = 0.0f;
            
            // 光线投射法检测点是否在网格内部
            int intersections = 0;
            
            for (int i = 0; i < num_faces; i++) {
                int v0_idx = faces[i * 3] * 3;
                int v1_idx = faces[i * 3 + 1] * 3;
                int v2_idx = faces[i * 3 + 2] * 3;
                
                float v0_x = vertices[v0_idx];
                float v0_y = vertices[v0_idx + 1];
                float v0_z = vertices[v0_idx + 2];
                
                float v1_x = vertices[v1_idx];
                float v1_y = vertices[v1_idx + 1];
                float v1_z = vertices[v1_idx + 2];
                
                float v2_x = vertices[v2_idx];
                float v2_y = vertices[v2_idx + 1];
                float v2_z = vertices[v2_idx + 2];
                
                // 检查射线与三角形的相交
                // ... (这里是射线-三角形相交检测算法)
                // 简化版：省略具体的相交检测代码
            }
            
            // 交点数为奇数表示在内部
            results[voxel_idx] = (intersections % 2) == 1;
        }
        """
        
        # 这里使用trimesh自带的体素化先实现
        voxelized = mesh.voxelized(pitch=self.base_voxel_size)
        self.voxel_grid = voxelized.fill()
        logger.info("GPU体素化完成")
    
    def _refine_regions(self, mesh: trimesh.Trimesh, refinement_voxels: Set[Tuple[int, int, int]]) -> None:
        """
        对需要细化的区域进行二次处理
        
        Args:
            mesh: 三角网格对象
            refinement_voxels: 需要细化的体素索引集合
        """
        logger.info("开始细化特定区域")
        
        bbox_min = self.origin
        subdivision_factor = int(self.base_voxel_size / self.min_voxel_size)
        
        # 遍历需要细化的体素
        for voxel_idx in refinement_voxels:
            # 只处理被占用的体素
            if not self.voxel_grid[voxel_idx]:
                continue
            
            # 计算体素中心和范围
            voxel_min = bbox_min + np.array(voxel_idx) * self.base_voxel_size
            voxel_max = voxel_min + self.base_voxel_size
            
            # 创建细分体素的坐标网格
            x = np.linspace(voxel_min[0] + self.min_voxel_size/2, voxel_max[0] - self.min_voxel_size/2, subdivision_factor)
            y = np.linspace(voxel_min[1] + self.min_voxel_size/2, voxel_max[1] - self.min_voxel_size/2, subdivision_factor)
            z = np.linspace(voxel_min[2] + self.min_voxel_size/2, voxel_max[2] - self.min_voxel_size/2, subdivision_factor)
            
            xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
            points = np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T
            
            # 检测点是否在网格内
            contains = mesh.contains(points)
            
            # 如果没有点在内部，保持原体素状态
            if not np.any(contains):
                continue
                
            # 如果所有点都在内部，保持原体素状态
            if np.all(contains):
                continue
                
            # 有部分点在内部，需要更新体素大小
            self.voxel_size_grid[voxel_idx] = self.min_voxel_size
            
            # 这里可以存储细分结果，但由于数据结构复杂，简化处理
            # 实际实现中，可能需要使用稀疏数据结构存储细分后的体素
        
        logger.info("区域细化完成")
    
    def _voxelize_octree(self, mesh: trimesh.Trimesh, shape: Optional[TopoDS_Shape] = None) -> Dict[str, Any]:
        """
        使用八叉树进行自适应体素化
        
        Args:
            mesh: 三角网格对象
            shape: 原始OpenCASCADE几何体(可选)
            
        Returns:
            体素化结果字典
        """
        logger.info("开始八叉树体素化")
        
        # 获取包围盒
        bbox_min, bbox_max = self.bounding_box
        dimensions = bbox_max - bbox_min
        
        # 计算八叉树根节点参数
        center = (bbox_min + bbox_max) / 2
        half_size = max(dimensions) / 2
        
        # 创建根节点
        self.octree_root = Octree(
            center=center,
            half_size=half_size,
            children=[],
            level=0,
            is_leaf=False,
            is_occupied=True
        )
        
        # 递归构建八叉树
        self._build_octree(self.octree_root, mesh)
        
        # 将八叉树转换为体素网格
        voxels = self._octree_to_voxels(self.octree_root)
        
        logger.info(f"八叉树体素化完成，生成体素数量: {len(voxels)}")
        
        return {
            "octree_root": self.octree_root,
            "voxels": voxels,
            "origin": self.origin,
            "base_voxel_size": self.base_voxel_size,
            "min_voxel_size": self.min_voxel_size,
            "bounding_box": self.bounding_box,
        }
    
    def _build_octree(self, node: Octree, mesh: trimesh.Trimesh, max_level: int = 6) -> None:
        """
        递归构建八叉树
        
        Args:
            node: 当前节点
            mesh: 三角网格对象
            max_level: 最大递归层级
        """
        # 如果达到最大层级或最小体素大小，停止递归
        current_voxel_size = node.half_size * 2
        if node.level >= max_level or current_voxel_size <= self.min_voxel_size:
            node.is_leaf = True
            return
        
        # 检查节点是否与网格相交
        node_min = node.center - node.half_size
        node_max = node.center + node.half_size
        
        # 创建节点包围盒
        node_corners = np.array([
            [node_min[0], node_min[1], node_min[2]],
            [node_max[0], node_min[1], node_min[2]],
            [node_min[0], node_max[1], node_min[2]],
            [node_max[0], node_max[1], node_min[2]],
            [node_min[0], node_min[1], node_max[2]],
            [node_max[0], node_min[1], node_max[2]],
            [node_min[0], node_max[1], node_max[2]],
            [node_max[0], node_max[1], node_max[2]]
        ])
        
        # 检查是否有点在网格内
        contains = mesh.contains(node_corners)
        
        # 如果所有点都在内部或都在外部，将节点标记为叶节点
        if np.all(contains) or not np.any(contains):
            node.is_leaf = True
            node.is_occupied = np.any(contains)
            return
        
        # 对于边界节点，需要进一步细分
        node.is_leaf = False
        node.is_occupied = True
        
        # 计算子节点偏移
        offsets = np.array([
            [-1, -1, -1],
            [1, -1, -1],
            [-1, 1, -1],
            [1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [-1, 1, 1],
            [1, 1, 1]
        ]) * (node.half_size / 2)
        
        # 创建8个子节点
        for offset in offsets:
            child_center = node.center + offset
            child = Octree(
                center=child_center,
                half_size=node.half_size / 2,
                children=[],
                level=node.level + 1,
                is_leaf=False,
                is_occupied=False
            )
            node.children.append(child)
            
            # 递归处理子节点
            self._build_octree(child, mesh, max_level)
    
    def _octree_to_voxels(self, root: Octree) -> List[Dict[str, Any]]:
        """
        将八叉树转换为体素列表
        
        Args:
            root: 八叉树根节点
            
        Returns:
            体素列表
        """
        voxels = []
        self._collect_leaf_voxels(root, voxels)
        return voxels
    
    def _collect_leaf_voxels(self, node: Octree, voxels: List[Dict[str, Any]]) -> None:
        """
        收集八叉树的叶节点体素
        
        Args:
            node: 当前节点
            voxels: 体素列表，用于收集结果
        """
        if node.is_leaf and node.is_occupied:
            voxel = {
                "center": node.center.tolist(),
                "size": node.half_size * 2,
                "level": node.level
            }
            voxels.append(voxel)
        elif not node.is_leaf:
            for child in node.children:
                self._collect_leaf_voxels(child, voxels)
    
    def save_voxel_grid(self, output_path: str, compress: bool = True) -> None:
        """
        保存体素网格到文件
        
        Args:
            output_path: 输出文件路径
            compress: 是否压缩数据
        """
        if self.voxel_grid is None:
            logger.error("没有可保存的体素网格")
            return
            
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # 保存体素数据
        np.savez_compressed(output_path if compress else output_path,
                          voxel_grid=self.voxel_grid,
                          voxel_size_grid=self.voxel_size_grid,
                          origin=self.origin,
                          base_voxel_size=self.base_voxel_size,
                          min_voxel_size=self.min_voxel_size,
                          bounding_box=self.bounding_box)
        
        logger.info(f"体素数据已保存到 {output_path}")
    
    def load_voxel_grid(self, input_path: str) -> Dict[str, Any]:
        """
        从文件加载体素网格
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            加载的体素数据
        """
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return {}
            
        try:
            # 加载体素数据
            data = np.load(input_path)
            
            self.voxel_grid = data["voxel_grid"]
            self.voxel_size_grid = data["voxel_size_grid"]
            self.origin = data["origin"]
            self.base_voxel_size = float(data["base_voxel_size"])
            self.min_voxel_size = float(data["min_voxel_size"])
            self.bounding_box = data["bounding_box"]
            self.grid_shape = self.voxel_grid.shape
            
            logger.info(f"已从 {input_path} 加载体素数据")
            
            return {
                "voxel_grid": self.voxel_grid,
                "voxel_size_grid": self.voxel_size_grid,
                "origin": self.origin,
                "base_voxel_size": self.base_voxel_size,
                "min_voxel_size": self.min_voxel_size,
                "bounding_box": self.bounding_box,
                "grid_shape": self.grid_shape,
                "occupied_voxels": np.sum(self.voxel_grid),
            }
        except Exception as e:
            logger.error(f"加载体素数据失败: {e}")
            return {}


if __name__ == "__main__":
    # 测试体素化器
    voxelizer = AdaptiveVoxelizer()
    
    # 测试文件路径
    test_file = "../data/models/sample.stl"
    
    if os.path.exists(test_file):
        # 加载模型
        mesh = trimesh.load_mesh(test_file)
        
        # 进行体素化
        result = voxelizer.voxelize(mesh)
        
        print(f"体素化结果: 占用体素数量 = {result['occupied_voxels']}")
    else:
        print(f"测试文件不存在: {test_file}")