"""
File: src/utils/geometry_utils.py
几何计算工具
提供基本的几何计算和转换功能
"""

import os
import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Set, Union, Any
import math
from pathlib import Path

# 第三方库导入
import trimesh
from scipy.spatial import ConvexHull, Delaunay, cKDTree
import networkx as nx
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex
from OCC.Core.BRep import BRep_Tool
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties, brepgprop_VolumeProperties
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Extend.TopologyUtils import TopologyExplorer
from scipy.ndimage import label, generate_binary_structure

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("geometry_utils")


def convert_occ_shape_to_trimesh(shape: TopoDS_Shape, mesh_precision: float = 0.1) -> trimesh.Trimesh:
    """
    将OpenCASCADE几何体转换为trimesh对象
    
    Args:
        shape: OpenCASCADE几何体
        mesh_precision: 网格化精度
        
    Returns:
        转换后的trimesh对象
    """
    # 进行网格化
    mesh = BRepMesh_IncrementalMesh(shape, mesh_precision, False, 0.1, True)
    mesh.Perform()
    
    # 收集所有面的顶点和三角形
    vertices = []
    triangles = []
    vertex_map = {}  # 用于去重顶点
    
    # 遍历所有面
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS_Face(explorer.Current())
        location = TopLoc_Location()
        
        # 获取面的三角化
        triangulation = BRep_Tool.Triangulation(face, location)
        if triangulation is None:
            explorer.Next()
            continue
            
        # 处理变换矩阵
        trsf = location.Transformation()
        
        # 收集顶点
        for i in range(1, triangulation.NbNodes() + 1):
            pnt = triangulation.Node(i)
            # 应用变换
            transformed_pnt = pnt.Transformed(trsf)
            # 顶点坐标
            vertex = (transformed_pnt.X(), transformed_pnt.Y(), transformed_pnt.Z())
            
            # 查找或添加顶点
            vertex_idx = vertex_map.get(vertex)
            if vertex_idx is None:
                vertex_idx = len(vertices)
                vertex_map[vertex] = vertex_idx
                vertices.append(vertex)
        
        # 收集三角形
        for i in range(1, triangulation.NbTriangles() + 1):
            triangle = triangulation.Triangle(i)
            # 三角形索引，注意OpenCASCADE从1开始索引
            idx1, idx2, idx3 = triangle.Get()
            # 转换为全局顶点索引
            v1 = triangulation.Node(idx1)
            v2 = triangulation.Node(idx2)
            v3 = triangulation.Node(idx3)
            
            # 应用变换
            v1 = v1.Transformed(trsf)
            v2 = v2.Transformed(trsf)
            v3 = v3.Transformed(trsf)
            
            # 转换为顶点索引
            v1_idx = vertex_map.get((v1.X(), v1.Y(), v1.Z()))
            v2_idx = vertex_map.get((v2.X(), v2.Y(), v2.Z()))
            v3_idx = vertex_map.get((v3.X(), v3.Y(), v3.Z()))
            
            if v1_idx is not None and v2_idx is not None and v3_idx is not None:
                triangles.append([v1_idx, v2_idx, v3_idx])
                
        explorer.Next()
    
    # 创建trimesh对象
    mesh = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(triangles))
    return mesh


def calculate_shape_properties(shape: TopoDS_Shape) -> Dict[str, float]:
    """
    计算OpenCASCADE几何体的基本属性
    
    Args:
        shape: OpenCASCADE几何体
        
    Returns:
        几何体的基本属性字典，包含体积、表面积、质心等
    """
    # 计算体积属性
    volume_props = GProp_GProps()
    brepgprop_VolumeProperties(shape, volume_props)
    
    # 计算表面属性
    surface_props = GProp_GProps()
    brepgprop_SurfaceProperties(shape, surface_props)
    
    # 获取质心
    com = volume_props.CentreOfMass()
    center_of_mass = (com.X(), com.Y(), com.Z())
    
    # 获取体积和表面积
    volume = volume_props.Mass()
    surface_area = surface_props.Mass()
    
    # 计算包围盒
    bbox_min = [float('inf'), float('inf'), float('inf')]
    bbox_max = [float('-inf'), float('-inf'), float('-inf')]
    
    # 遍历所有顶点更新包围盒
    explorer = TopExp_Explorer(shape, TopAbs_VERTEX)
    while explorer.More():
        vertex = TopoDS_Vertex(explorer.Current())
        point = BRep_Tool.Pnt(vertex)
        
        # 更新最小值
        bbox_min[0] = min(bbox_min[0], point.X())
        bbox_min[1] = min(bbox_min[1], point.Y())
        bbox_min[2] = min(bbox_min[2], point.Z())
        
        # 更新最大值
        bbox_max[0] = max(bbox_max[0], point.X())
        bbox_max[1] = max(bbox_max[1], point.Y())
        bbox_max[2] = max(bbox_max[2], point.Z())
        
        explorer.Next()
    
    # 计算尺寸
    dimensions = [
        bbox_max[0] - bbox_min[0],
        bbox_max[1] - bbox_min[1], 
        bbox_max[2] - bbox_min[2]
    ]
    
    # 返回属性字典
    return {
        "volume": volume,
        "surface_area": surface_area,
        "center_of_mass": center_of_mass,
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "dimensions": dimensions
    }


def calculate_shape_distance(shape1: TopoDS_Shape, shape2: TopoDS_Shape) -> float:
    """
    计算两个几何体之间的最小距离
    
    Args:
        shape1: 第一个OpenCASCADE几何体
        shape2: 第二个OpenCASCADE几何体
        
    Returns:
        两个几何体之间的最小距离
    """
    distance_calculator = BRepExtrema_DistShapeShape(shape1, shape2)
    distance_calculator.Perform()
    
    if distance_calculator.IsDone():
        return distance_calculator.Value()
    else:
        logger.warning("Distance calculation failed")
        return float('inf')


def voxelize_points(points: np.ndarray, voxel_size: float) -> Tuple[np.ndarray, Dict]:
    """
    将点云体素化为离散网格
    
    Args:
        points: 点云数组，形状为(n, 3)
        voxel_size: 体素大小
        
    Returns:
        体素中心点数组和体素字典
    """
    # 计算体素索引
    voxel_indices = np.floor(points / voxel_size).astype(int)
    
    # 创建体素字典，键为体素索引，值为体素内的点索引
    voxel_dict = {}
    for i, idx in enumerate(voxel_indices):
        idx_tuple = tuple(idx)
        if idx_tuple in voxel_dict:
            voxel_dict[idx_tuple].append(i)
        else:
            voxel_dict[idx_tuple] = [i]
    
    # 计算体素中心点
    voxel_centers = np.array(list(voxel_dict.keys())) * voxel_size + voxel_size / 2
    
    return voxel_centers, voxel_dict


def calculate_curvature(mesh: trimesh.Trimesh, radius: Optional[float] = None) -> np.ndarray:
    """
    计算三角网格的曲率
    
    Args:
        mesh: trimesh对象
        radius: 考虑邻居的半径，如果为None则自动计算
        
    Returns:
        每个顶点的曲率值数组
    """
    if radius is None:
        # 自动计算合适的半径，约为平均边长的2倍
        radius = np.mean(mesh.edges_unique_length) * 2
    
    # 计算每个顶点的法向量差异作为曲率估计
    curvature = np.zeros(len(mesh.vertices))
    
    # 使用KDTree查找邻近顶点
    tree = mesh.kdtree
    
    for i, vertex in enumerate(mesh.vertices):
        # 查找邻近顶点
        indices = tree.query_ball_point(vertex, radius)
        if len(indices) < 3:
            continue
            
        # 计算邻近法向量的协方差矩阵
        normals = mesh.vertex_normals[indices]
        cov = np.cov(normals, rowvar=False)
        
        # 计算特征值作为主曲率
        try:
            eigenvalues = np.linalg.eigvalsh(cov)
            # 使用最小特征值作为曲率估计
            curvature[i] = eigenvalues[0]
        except np.linalg.LinAlgError:
            # 处理奇异矩阵
            curvature[i] = 0
    
    return curvature


def find_narrow_passages(voxels: np.ndarray, threshold: float) -> np.ndarray:
    """
    在体素网格中查找窄通道
    
    Args:
        voxels: 体素坐标数组
        threshold: 窄通道宽度阈值
        
    Returns:
        窄通道体素的索引数组
    """
    # 构建KD树用于邻域查询
    tree = cKDTree(voxels)
    
    # 计算每个体素到最近空间边界的距离
    distances, _ = tree.query(voxels, k=2)  # k=2 获取最近邻(除自身外)
    distances = distances[:, 1]  # 取第二近的点(第一个是自身)
    
    # 找出距离小于阈值的体素（窄通道）
    narrow_indices = np.where(distances < threshold)[0]
    
    return narrow_indices


def compute_opening_features(vertices: np.ndarray) -> Dict[str, float]:
    """
    计算开口（门/通道）的几何特征
    
    Args:
        vertices: 开口边界的顶点坐标
        
    Returns:
        开口特征字典
    """
    if len(vertices) < 3:
        logger.warning("Not enough vertices to compute opening features")
        return {
            "area": 0.0,
            "perimeter": 0.0,
            "width": 0.0,
            "height": 0.0,
            "aspect_ratio": 0.0,
            "circularity": 0.0
        }
    
    # 计算2D投影（假设开口大致在一个平面上）
    # 首先找到主平面
    hull = ConvexHull(vertices)
    centroid = np.mean(vertices, axis=0)
    
    # 使用PCA找到主平面
    points_centered = vertices - centroid
    cov = np.cov(points_centered, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    
    # 最小特征值对应的特征向量是法向量
    normal = eigvecs[:, 0]
    
    # 创建投影平面的基向量
    if np.abs(normal[2]) > 0.9:
        # 如果法向量接近z轴，使用x和y轴作为基向量
        basis1 = np.array([1, 0, 0])
        basis2 = np.array([0, 1, 0])
    else:
        # 否则使用叉积计算基向量
        basis1 = np.cross(normal, np.array([0, 0, 1]))
        basis1 = basis1 / np.linalg.norm(basis1)
        basis2 = np.cross(normal, basis1)
        basis2 = basis2 / np.linalg.norm(basis2)
    
    # 投影到2D平面
    vertices_2d = np.column_stack([
        np.dot(points_centered, basis1),
        np.dot(points_centered, basis2)
    ])
    
    # 计算2D凸包
    hull_2d = ConvexHull(vertices_2d)
    area = hull_2d.volume  # 2D中volume其实是面积
    
    # 计算周长
    perimeter = 0
    for simplex in hull_2d.simplices:
        p1 = vertices_2d[simplex[0]]
        p2 = vertices_2d[simplex[1]]
        perimeter += np.linalg.norm(p2 - p1)
    
    # 计算包围盒和尺寸
    min_x = np.min(vertices_2d[:, 0])
    max_x = np.max(vertices_2d[:, 0])
    min_y = np.min(vertices_2d[:, 1])
    max_y = np.max(vertices_2d[:, 1])
    
    width = max_x - min_x
    height = max_y - min_y
    
    # 调整，确保宽度大于高度
    if width < height:
        width, height = height, width
    
    # 计算纵横比
    aspect_ratio = width / height if height > 0 else 0
    
    # 计算圆形度 (4π*面积/周长²)
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
    
    # 计算高度范围（在法向量方向上的投影范围）
    heights = np.dot(points_centered, normal)
    height_range = np.max(heights) - np.min(heights)
    
    # 返回特征字典
    return {
        "area": area,
        "perimeter": perimeter,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "circularity": circularity,
        "height_range": height_range,
        "normal": normal.tolist(),
        "centroid": centroid.tolist()
    }


def ray_casting(point: np.ndarray, mesh: trimesh.Trimesh, directions: Optional[np.ndarray] = None, 
               num_rays: int = 6) -> bool:
    """
    使用光线投射确定点是否在封闭网格内部
    
    Args:
        point: 要检查的点
        mesh: trimesh网格对象
        directions: 光线投射方向，如果为None则使用均匀分布的方向
        num_rays: 投射的光线数量
        
    Returns:
        如果点在网格内部则为True，否则为False
    """
    if directions is None:
        # 创建均匀分布的方向
        phi = np.linspace(0, 2 * np.pi, num_rays, endpoint=False)
        theta = np.linspace(0, np.pi, num_rays // 2, endpoint=False)
        
        directions = []
        for t in theta:
            for p in phi:
                x = np.sin(t) * np.cos(p)
                y = np.sin(t) * np.sin(p)
                z = np.cos(t)
                directions.append([x, y, z])
        
        directions = np.array(directions)
    
    # 确保方向是单位向量
    directions = directions / np.linalg.norm(directions, axis=1)[:, np.newaxis]
    
    # 进行光线投射并计算相交次数
    intersections = 0
    for direction in directions:
        # 创建射线
        ray_origins = np.array([point])
        ray_directions = np.array([direction])
        
        # 计算相交
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=ray_origins,
            ray_directions=ray_directions
        )
        
        # 计算相交次数
        intersections += len(locations)
    
    # 奇数个相交点表示在内部，偶数个表示在外部
    return (intersections % 2) == 1


def find_connected_components(voxel_grid: np.ndarray, connectivity: int = 6) -> List[np.ndarray]:
    """
    在体素网格中找到连通区域
    
    Args:
        voxel_grid: 体素网格，非零值表示占用
        connectivity: 连通性（6=面连通，18=边连通，26=顶点连通）
        
    Returns:
        连通区域列表，每个元素是一个体素索引数组
    """
    # 创建连通性结构元素
    if connectivity == 6:
        # 面连通 (6-连通)
        struct = generate_binary_structure(3, 1)
    elif connectivity == 18:
        # 边连通 (18-连通)
        struct = generate_binary_structure(3, 2)
    elif connectivity == 26:
        # 顶点连通 (26-连通)
        struct = generate_binary_structure(3, 3)
    else:
        raise ValueError(f"Unsupported connectivity: {connectivity}")
    
    # 标记连通区域
    labeled_array, num_features = label(voxel_grid, structure=struct)
    
    # 收集每个连通区域的体素索引
    components = []
    for i in range(1, num_features + 1):
        component_indices = np.where(labeled_array == i)
        # 转换为坐标列表
        component_coords = np.column_stack(component_indices)
        components.append(component_coords)
    
    return components


def voxel_grid_to_mesh(voxel_grid: np.ndarray, voxel_size: float, origin: np.ndarray = np.zeros(3)) -> trimesh.Trimesh:
    """
    将体素网格转换为三角网格
    
    Args:
        voxel_grid: 3D体素网格，True表示占用
        voxel_size: 体素大小
        origin: 网格原点
        
    Returns:
        体素网格的三角网格表示
    """
    # 找到所有占用体素
    voxel_indices = np.where(voxel_grid)
    voxel_coords = np.column_stack(voxel_indices)
    
    # 创建空网格
    mesh = trimesh.Trimesh()
    
    # 如果没有体素，返回空网格
    if len(voxel_coords) == 0:
        return mesh
    
    # 为每个体素创建立方体
    for coord in voxel_coords:
        # 计算体素中心
        center = origin + (coord + 0.5) * voxel_size
        
        # 创建立方体
        cube = trimesh.creation.box(extents=[voxel_size] * 3, transform=np.eye(4))
        cube.apply_translation(center)
        
        # 合并到主网格
        mesh = trimesh.util.concatenate([mesh, cube])
    
    # 合并重复顶点
    mesh.merge_vertices()
    
    return mesh


def compute_medial_axis(voxel_grid: np.ndarray) -> np.ndarray:
    """
    计算体素网格的中轴骨架
    
    Args:
        voxel_grid: 3D体素网格，True表示占用
        
    Returns:
        中轴骨架的体素网格
    """
    from skimage.morphology import skeletonize_3d
    
    # 使用3D骨架化计算中轴
    skeleton = skeletonize_3d(voxel_grid)
    
    return skeleton


def create_graph_from_skeleton(skeleton: np.ndarray, voxel_size: float, 
                              origin: np.ndarray = np.zeros(3)) -> nx.Graph:
    """
    从骨架创建网络图
    
    Args:
        skeleton: 骨架体素网格
        voxel_size: 体素大小
        origin: 网格原点
        
    Returns:
        骨架的网络图表示
    """
    # 创建空图
    graph = nx.Graph()
    
    # 找到所有骨架体素
    indices = np.where(skeleton)
    coords = np.column_stack(indices)
    
    # 添加节点
    for i, coord in enumerate(coords):
        # 计算真实世界坐标
        position = origin + coord * voxel_size
        graph.add_node(i, position=position.tolist(), voxel_coord=coord.tolist())
    
    # 计算邻居关系 (26-连通)
    coords_set = set(tuple(coord) for coord in coords)
    
    # 遍历所有骨架体素
    for i, coord in enumerate(coords):
        # 检查26个邻居
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                        
                    neighbor = (coord[0] + dx, coord[1] + dy, coord[2] + dz)
                    
                    # 如果邻居是骨架的一部分
                    if neighbor in coords_set:
                        # 找到邻居的索引
                        neighbor_idx = np.where((coords == neighbor).all(axis=1))[0][0]
                        
                        # 计算距离
                        dist = np.sqrt(dx**2 + dy**2 + dz**2) * voxel_size
                        
                        # 添加边
                        graph.add_edge(i, neighbor_idx, weight=dist)
    
    return graph


def classify_skeleton_points(graph: nx.Graph) -> Dict[int, str]:
    """
    对骨架点进行分类（端点、分支点、通道点）
    
    Args:
        graph: 骨架的网络图表示
        
    Returns:
        点分类字典，键为节点ID，值为分类标签
    """
    classification = {}
    
    for node in graph.nodes():
        degree = graph.degree(node)
        
        if degree == 1:
            # 端点
            classification[node] = "endpoint"
        elif degree > 2:
            # 分支点
            classification[node] = "junction"
        else:
            # 通道点
            classification[node] = "passage"
    
    return classification


def extract_paths_between_junctions(graph: nx.Graph, classification: Dict[int, str]) -> List[List[int]]:
    """
    提取骨架中的路径（从分支点到分支点或端点）
    
    Args:
        graph: 骨架的网络图表示
        classification: 点分类字典
        
    Returns:
        路径列表，每个路径是节点ID列表
    """
    # 找到所有分支点和端点
    special_points = [node for node, cls in classification.items() 
                     if cls in ("junction", "endpoint")]
    
    # 创建子图，仅包含特殊点
    subgraph = graph.copy()
    
    # 对于每两个特殊点，找到它们之间的最短路径
    paths = []
    for i, start in enumerate(special_points):
        for end in special_points[i+1:]:
            if nx.has_path(graph, start, end):
                # 找到最短路径
                path = nx.shortest_path(graph, start, end, weight='weight')
                
                # 检查路径中是否包含其他分支点
                contains_other_junction = False
                for node in path[1:-1]:
                    if classification.get(node) == "junction":
                        contains_other_junction = True
                        break
                
                if not contains_other_junction:
                    paths.append(path)
    
    return paths


def compute_opening_direction(vertices: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    计算开口的方向向量和平面度
    
    Args:
        vertices: 开口的顶点坐标
        
    Returns:
        方向向量和平面度（0-1，值越大越平）
    """
    # 计算中心点
    center = np.mean(vertices, axis=0)
    
    # 使用PCA找到主方向
    points_centered = vertices - center
    cov = np.cov(points_centered, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    
    # 最小特征值对应的特征向量是法向量
    normal = eigvecs[:, 0]
    
    # 计算平面度 (0-1，值越大越平)
    planarity = 1.0 - (eigvals[0] / (eigvals[1] + 1e-10))
    
    return normal, planarity


def compute_boundingbox_features(vertices: np.ndarray) -> Dict[str, float]:
    """
    计算点集的包围盒特征
    
    Args:
        vertices: 点坐标数组
        
    Returns:
        包围盒特征字典
    """
    # 计算包围盒
    min_coords = np.min(vertices, axis=0)
    max_coords = np.max(vertices, axis=0)
    
    # 计算包围盒尺寸
    dimensions = max_coords - min_coords
    
    # 计算体积和表面积
    volume = np.prod(dimensions)
    surface_area = 2 * (dimensions[0] * dimensions[1] + 
                       dimensions[0] * dimensions[2] + 
                       dimensions[1] * dimensions[2])
    
    # 排序尺寸（大到小）
    sorted_dims = np.sort(dimensions)[::-1]
    
    # 计算宽高比
    aspect_ratio_1 = sorted_dims[0] / (sorted_dims[1] + 1e-10)
    aspect_ratio_2 = sorted_dims[1] / (sorted_dims[2] + 1e-10)
    
    # 计算紧凑度 (表面积^3 / (36*π*体积^2))
    compactness = surface_area**3 / (36 * np.pi * volume**2) if volume > 0 else float('inf')
    
    return {
        "volume": volume,
        "surface_area": surface_area,
        "dimensions": dimensions.tolist(),
        "aspect_ratio_1": aspect_ratio_1,
        "aspect_ratio_2": aspect_ratio_2,
        "compactness": compactness
    }


if __name__ == "__main__":
    # 测试函数
    print("Geometry utilities module")