#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: src/model_processing/format_parser.py
多格式解析器
支持多种CAD格式（STL、OBJ、IFC、STEP）的解析与转换

注意：当前项目主要采用 STEP 文件上传和解析。
"""

import os
import logging
import tempfile
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path

# 检查OpenCASCADE依赖是否可用
from . import OPENCASCADE_AVAILABLE

# 第三方库导入
import numpy as np
import trimesh

# 有条件地导入OpenCASCADE依赖
if OPENCASCADE_AVAILABLE:
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_SurfaceProperties, brepgprop_VolumeProperties
    from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Compound
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.StlAPI import StlAPI_Reader
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.gp import gp_Trsf, gp_Vec
    from OCC.Extend.DataExchange import read_step_file, read_iges_file, read_stl_file
    from OCC.Extend.TopologyUtils import TopologyExplorer
    from OCC.Core.TopoDS import topods_Face, topods_Edge, topods_Vertex
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX

# 本地模块导入
from ..config import get_config
from ..utils.geometry_utils import convert_occ_shape_to_trimesh, calculate_shape_properties

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("format_parser")


class FormatParser:
    """多格式解析器，支持多种CAD格式（STL、OBJ、IFC、STEP）的解析与转换
    当前项目主要采用 STEP 文件上传和解析。
    """
    def __init__(self):
        """初始化解析器"""
        self.config = get_config()
        
        # 只支持 STEP、IGES、STL、OBJ、IFC 文件
        self.supported_formats = {
            ".step": self._parse_step,
            ".stp": self._parse_step,
            ".iges": self._parse_iges,
            ".igs": self._parse_iges,
            ".stl": self._parse_stl,
            ".obj": self._parse_obj,
            ".ifc": self._parse_ifc,
        }
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析CAD文件，返回解析结果
        
        Args:
            file_path: CAD文件路径
            
        Returns:
            解析结果字典，包含几何体和属性
        """
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 检查是否支持该格式
        if file_ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        # 解析文件
        logger.info(f"正在解析文件: {file_path}")
        parse_func = self.supported_formats[file_ext]
        result = parse_func(file_path)
        
        # 添加文件信息
        result["file_info"] = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "format": file_ext[1:],  # 去掉点
            "size": os.path.getsize(file_path),
        }
        
        logger.info(f"文件解析完成: {file_path}")
        return result

    # 删除 _parse_solidworks 方法，因为项目现在只采用 STEP 文件解析

    def _parse_step(self, file_path: str) -> Dict[str, Any]:
        """
        解析STEP文件
        
        Args:
            file_path: STEP文件路径
            
        Returns:
            解析结果字典
        """
        if not OPENCASCADE_AVAILABLE:
            logger.error("OpenCASCADE依赖未安装，无法解析STEP文件")
            raise ImportError(
                "解析STEP文件需要OpenCASCADE依赖。在Windows环境中，请使用conda安装：\n"
                "conda install -c conda-forge pythonocc-core"
            )
            
        try:
            # 使用OpenCASCADE解析STEP文件
            shape = read_step_file(file_path)
            
            # 提取几何属性
            properties = calculate_shape_properties(shape)
            
            # 提取语义信息（如果有）
            semantic_info = self._extract_step_semantics(file_path)
            
            # 转换为trimesh
            mesh = convert_occ_shape_to_trimesh(shape)
            
            return {
                "shape": shape,
                "mesh": mesh,
                "properties": properties,
                "semantic_info": semantic_info,
            }
        except Exception as e:
            logger.error(f"解析STEP文件失败: {e}")
            # 在Windows环境中提供更详细的错误信息
            if "Windows" in os.name:
                logger.error("在Windows环境中，请确保使用conda正确安装了OpenCASCADE依赖")
            raise

    def _parse_iges(self, file_path: str) -> Dict[str, Any]:
        """
        解析IGES文件
        
        Args:
            file_path: IGES文件路径
            
        Returns:
            解析结果字典
        """
        if not OPENCASCADE_AVAILABLE:
            logger.error("OpenCASCADE依赖未安装，无法解析IGES文件")
            raise ImportError(
                "解析IGES文件需要OpenCASCADE依赖。在Windows环境中，请使用conda安装：\n"
                "conda install -c conda-forge pythonocc-core"
            )
            
        try:
            shape = read_iges_file(file_path)
            properties = calculate_shape_properties(shape)
            mesh = convert_occ_shape_to_trimesh(shape)
            return {
                "shape": shape,
                "mesh": mesh,
                "properties": properties,
                "semantic_info": {},
            }
        except Exception as e:
            logger.error(f"解析IGES文件失败: {e}")
            # 在Windows环境中提供更详细的错误信息
            if "Windows" in os.name:
                logger.error("在Windows环境中，请确保使用conda正确安装了OpenCASCADE依赖")
            raise

    def _parse_stl(self, file_path: str) -> Dict[str, Any]:
        """
        解析STL文件
        
        Args:
            file_path: STL文件路径
            
        Returns:
            解析结果字典
        """
        try:
            # 确保文件路径使用正确的分隔符
            file_path = str(Path(file_path))
            
            mesh = trimesh.load_mesh(file_path)
            if not isinstance(mesh, trimesh.Trimesh):
                if isinstance(mesh, trimesh.Scene):
                    geometries = list(mesh.geometry.values())
                    if len(geometries) > 0:
                        mesh = geometries[0]
                    else:
                        raise ValueError("STL文件不包含有效的网格")
                else:
                    raise ValueError(f"不支持的网格类型: {type(mesh)}")
            
            # 有条件地使用OpenCASCADE
            if OPENCASCADE_AVAILABLE:
                shape = read_stl_file(file_path)
            else:
                shape = None
                logger.warning("OpenCASCADE依赖未安装，STL文件将只使用trimesh处理")
                
            properties = {
                "volume": mesh.volume,
                "surface_area": mesh.area,
                "center_of_mass": mesh.center_mass.tolist(),
                "bbox_min": mesh.bounds[0].tolist(),
                "bbox_max": mesh.bounds[1].tolist(),
                "dimensions": (mesh.bounds[1] - mesh.bounds[0]).tolist(),
            }
            return {
                "shape": shape,
                "mesh": mesh,
                "properties": properties,
                "semantic_info": {},
            }
        except Exception as e:
            logger.error(f"解析STL文件失败: {e}")
            # 在Windows环境中提供更详细的错误信息
            if "Windows" in os.name:
                logger.error("在Windows环境中，请检查文件路径是否正确，并确保安装了trimesh库")
            raise

    def _parse_obj(self, file_path: str) -> Dict[str, Any]:
        """
        解析OBJ文件
        
        Args:
            file_path: OBJ文件路径
            
        Returns:
            解析结果字典
        """
        try:
            # 确保文件路径使用正确的分隔符
            file_path = str(Path(file_path))
            
            mesh = trimesh.load_mesh(file_path)
            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(
                    [trimesh.Trimesh(vertices=g.vertices, faces=g.faces)
                     for g in mesh.geometry.values()]
                )
                
            # 通过临时STL文件转换为OpenCASCADE几何体
            shape = None
            if OPENCASCADE_AVAILABLE:
                with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
                    tmp_path = str(Path(tmp_file.name))  # 确保路径格式正确
                try:
                    mesh.export(tmp_path)
                    shape = read_stl_file(tmp_path)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            else:
                logger.warning("OpenCASCADE依赖未安装，OBJ文件将只使用trimesh处理")
                
            properties = {
                "volume": mesh.volume,
                "surface_area": mesh.area,
                "center_of_mass": mesh.center_mass.tolist(),
                "bbox_min": mesh.bounds[0].tolist(),
                "bbox_max": mesh.bounds[1].tolist(),
                "dimensions": (mesh.bounds[1] - mesh.bounds[0]).tolist(),
            }
            materials = {}
            if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'material'):
                material = mesh.visual.material
                materials = {
                    "ambient": material.ambient.tolist() if hasattr(material, 'ambient') else None,
                    "diffuse": material.diffuse.tolist() if hasattr(material, 'diffuse') else None,
                    "specular": material.specular.tolist() if hasattr(material, 'specular') else None,
                }
            return {
                "shape": shape,
                "mesh": mesh,
                "properties": properties,
                "semantic_info": {"materials": materials},
            }
        except Exception as e:
            logger.error(f"解析OBJ文件失败: {e}")
            # 在Windows环境中提供更详细的错误信息
            if "Windows" in os.name:
                logger.error("在Windows环境中，请检查文件路径是否正确，并确保安装了trimesh库")
            raise

    def _parse_ifc(self, file_path: str) -> Dict[str, Any]:
        """
        解析IFC文件
        
        Args:
            file_path: IFC文件路径
            
        Returns:
            解析结果字典
        """
        try:
            try:
                import ifcopenshell
            except ImportError:
                logger.error("未安装ifcopenshell库，无法解析IFC文件")
                raise ImportError("解析IFC文件需要安装ifcopenshell库")
            
            ifc_file = ifcopenshell.open(file_path)
            
            spaces = []
            for space in ifc_file.by_type("IfcSpace"):
                space_info = {
                    "id": space.GlobalId,
                    "name": space.Name if hasattr(space, 'Name') else "",
                    "long_name": space.LongName if hasattr(space, 'LongName') else "",
                    "type": "space",
                }
                spaces.append(space_info)
            
            doors = []
            for door in ifc_file.by_type("IfcDoor"):
                door_info = {
                    "id": door.GlobalId,
                    "name": door.Name if hasattr(door, 'Name') else "",
                    "type": "door",
                }
                doors.append(door_info)
            
            with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            try:
                ifc_file.write(tmp_path)
                step_result = self._parse_step(tmp_path)
                shape = step_result["shape"]
                mesh = step_result["mesh"]
                properties = step_result["properties"]
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            semantic_info = {
                "spaces": spaces,
                "doors": doors,
                "building_elements": [
                    {"type": elem_type, "count": len(list(ifc_file.by_type(elem_type)))}
                    for elem_type in ["IfcWall", "IfcWindow", "IfcColumn", "IfcBeam", "IfcSlab"]
                ]
            }
            
            return {
                "shape": shape,
                "mesh": mesh,
                "properties": properties,
                "semantic_info": semantic_info,
                "ifc_file": ifc_file,
            }
        except Exception as e:
            logger.error(f"解析IFC文件失败: {e}")
            raise

    def _extract_step_semantics(self, file_path: str) -> Dict[str, Any]:
        """
        从STEP文件中提取语义信息
        
        Args:
            file_path: STEP文件路径
            
        Returns:
            语义信息字典
        """
        semantic_info = {"entities": {}}
        
        try:
            with open(file_path, 'r', errors='ignore') as f:
                lines = [f.readline() for _ in range(1000)]
                
            for line in lines:
                if '=' in line and 'IFCSPACE' in line.upper():
                    semantic_info["entities"]["space"] = semantic_info["entities"].get("space", 0) + 1
                elif '=' in line and 'IFCDOOR' in line.upper():
                    semantic_info["entities"]["door"] = semantic_info["entities"].get("door", 0) + 1
                elif '=' in line and 'IFCWINDOW' in line.upper():
                    semantic_info["entities"]["window"] = semantic_info["entities"].get("window", 0) + 1
                elif '=' in line and 'IFCWALL' in line.upper():
                    semantic_info["entities"]["wall"] = semantic_info["entities"].get("wall", 0) + 1
        except Exception as e:
            logger.warning(f"提取STEP语义信息失败: {e}")
        
        return semantic_info

    def extract_topological_info(self, shape: TopoDS_Shape) -> Dict[str, Any]:
        """
        提取几何体的拓扑信息
        
        Args:
            shape: OpenCASCADE几何体
            
        Returns:
            拓扑信息字典
        """
        explorer = TopologyExplorer(shape)
        
        n_vertices = sum(1 for _ in explorer.vertices())
        n_edges = sum(1 for _ in explorer.edges())
        n_faces = sum(1 for _ in explorer.faces())
        n_solids = sum(1 for _ in explorer.solids())
        
        faces_info = []
        for i, face in enumerate(explorer.faces()):
            face_props = GProp_GProps()
            brepgprop_SurfaceProperties(face, face_props)
            area = face_props.Mass()
            
            faces_info.append({
                "id": i,
                "area": area,
            })
        
        edge_to_faces = {}
        for edge in explorer.edges():
            connected_faces = []
            for face in explorer.faces_from_edge(edge):
                face_idx = list(explorer.faces()).index(face)
                connected_faces.append(face_idx)
            
            edge_idx = list(explorer.edges()).index(edge)
            edge_to_faces[edge_idx] = connected_faces
        
        return {
            "n_vertices": n_vertices,
            "n_edges": n_edges,
            "n_faces": n_faces,
            "n_solids": n_solids,
            "faces": faces_info,
            "edge_to_faces": edge_to_faces,
        }

    def export_to_format(self, shape: TopoDS_Shape, output_path: str, 
                        format_type: str = "stl") -> str:
        """
        将OpenCASCADE几何体导出为指定格式
        
        Args:
            shape: OpenCASCADE几何体
            output_path: 输出文件路径
            format_type: 输出格式类型
            
        Returns:
            输出文件的绝对路径
        """
        format_type = format_type.lower()
        
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        if format_type == "stl":
            from OCC.Core.StlAPI import StlAPI_Writer
            stl_writer = StlAPI_Writer()
            stl_writer.SetASCIIMode(True)
            stl_writer.Write(shape, output_path)
        elif format_type == "step":
            from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
            from OCC.Core.Interface import Interface_Static
            Interface_Static.SetCVal("write.step.schema", "AP203")
            step_writer = STEPControl_Writer()
            step_writer.Transfer(shape, STEPControl_AsIs)
            step_writer.Write(output_path)
        elif format_type == "iges":
            from OCC.Core.IGESControl import IGESControl_Writer
            iges_writer = IGESControl_Writer()
            iges_writer.AddShape(shape)
            iges_writer.Write(output_path)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")
        
        return os.path.abspath(output_path)


if __name__ == "__main__":
    parser = FormatParser()
    test_file = "../data/models/sample.step"
    if os.path.exists(test_file):
        result = parser.parse_file(test_file)
        print(f"解析结果: {result['properties']}")
    else:
        print(f"测试文件不存在: {test_file}")
