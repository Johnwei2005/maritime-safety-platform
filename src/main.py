"""
File: src/main.py
主程序入口
协调各个模块的工作流程，实现从模型导入到结果输出的完整过程
"""

import os
import sys
import logging
import time
import argparse
from typing import Dict, List, Tuple, Optional, Any
import json

# 本地模块导入
from config import get_config
from model_processing.format_parser import FormatParser
from model_processing.voxelizer import AdaptiveVoxelizer
from space_analysis.space_detector import SpaceDetector
from space_analysis.opening_detector import OpeningDetector
from ventilation.topology_builder import TopologyBuilder
from ventilation.ach_calculator import AchCalculator
from data_output.space_data_generator import SpaceDataGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('platform_analysis.log')
    ]
)
logger = logging.getLogger("main")


class PlatformAnalyzer:
    """平台分析器，协调各个模块完成分析流程"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化平台分析器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        # 加载配置
        self.config = get_config(config_path)
        
        # 初始化各模块
        self.format_parser = FormatParser()
        self.voxelizer = AdaptiveVoxelizer()
        self.space_detector = SpaceDetector()
        self.opening_detector = OpeningDetector()
        self.topology_builder = TopologyBuilder()
        self.ach_calculator = AchCalculator()
        self.data_generator = SpaceDataGenerator()
        
        # 分析结果
        self.parsed_model = None
        self.voxel_data = None
        self.spaces = None
        self.space_adjacency = None
        self.openings = None
        self.space_graph = None
        self.ach_rates = None
        self.final_data = None
        
        logger.info("平台分析器初始化完成")
    
    def run_analysis(self, model_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        运行完整分析流程
        
        Args:
            model_path: 模型文件路径
            output_file: 输出文件路径（可选）
            
        Returns:
            分析结果
        """
        start_time = time.time()
        logger.info(f"开始分析模型: {model_path}")
        
        try:
            # 步骤1: 解析模型
            logger.info("步骤 1/7: 解析模型")
            self.parsed_model = self.format_parser.parse_file(model_path)
            
            # 步骤2: 体素化
            logger.info("步骤 2/7: 体素化")
            self.voxel_data = self.voxelizer.voxelize(self.parsed_model["mesh"])
            
            # 步骤3: 检测空间
            logger.info("步骤 3/7: 检测空间")
            space_result = self.space_detector.detect_spaces(self.voxel_data)
            self.spaces = space_result["spaces"]
            self.space_adjacency = space_result["adjacency"]
            
            # 步骤4: 检测开口（门和通道）
            logger.info("步骤 4/7: 检测开口")
            opening_result = self.opening_detector.detect_openings(
                self.voxel_data, self.spaces, self.space_adjacency
            )
            self.openings = opening_result["openings"]
            
            # 步骤5: 构建拓扑网络
            logger.info("步骤 5/7: 构建拓扑网络")
            topology_result = self.topology_builder.build_topology(
                self.spaces, self.openings
            )
            self.space_graph = topology_result["space_graph"]
            
            # 步骤6: 计算通风率
            logger.info("步骤 6/7: 计算通风率")
            ventilation_result = self.ach_calculator.calculate_ach_rates(
                self.spaces, self.space_graph, topology_result["exterior_nodes"]
            )
            self.ach_rates = ventilation_result["ach_rates"]
            
            # 步骤7: 生成最终数据
            logger.info("步骤 7/7: 生成结果数据")
            self.final_data = self.data_generator.generate_space_data(
                self.spaces, self.openings, self.ach_rates,
                ventilation_result["ventilation_paths"], self.space_graph
            )
            
            # 保存结果（如果指定了输出文件）
            if output_file:
                self.data_generator.save_space_data(self.final_data, output_file)
            
            # 生成可视化数据
            viz_file = output_file.replace(".json", "_viz.json") if output_file else None
            self.data_generator.export_for_visualization(self.final_data, viz_file)
            
            # 计算总处理时间
            elapsed_time = time.time() - start_time
            logger.info(f"分析完成，总耗时: {elapsed_time:.2f}秒")
            
            # 返回分析统计信息
            return {
                "status": "success",
                "elapsed_time": elapsed_time,
                "spaces_count": len(self.spaces),
                "openings_count": len(self.openings),
                "model_file": model_path,
                "output_file": output_file
            }
            
        except Exception as e:
            logger.error(f"分析过程出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "model_file": model_path
            }
    
    def analyze_with_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据选项运行分析
        
        Args:
            options: 分析选项字典
            
        Returns:
            分析结果
        """
        # 提取选项
        model_path = options.get("model_path")
        output_file = options.get("output_file")
        
        # 应用自定义配置
        if "config_overrides" in options:
            self._apply_config_overrides(options["config_overrides"])
        
        # 运行分析
        return self.run_analysis(model_path, output_file)
    
    def _apply_config_overrides(self, overrides: Dict[str, Dict[str, Any]]) -> None:
        """
        应用配置覆盖
        
        Args:
            overrides: 配置覆盖字典
        """
        for section, params in overrides.items():
            for key, value in params.items():
                self.config.set(section, key, value)
                logger.info(f"覆盖配置 {section}.{key} = {value}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='海上平台空间分析工具')
    
    parser.add_argument('model_path', type=str, help='模型文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--config', '-c', type=str, help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='启用详细日志')
    
    return parser.parse_args()


def main():
    """主程序入口"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 检查模型文件是否存在
    if not os.path.exists(args.model_path):
        logger.error(f"模型文件不存在: {args.model_path}")
        sys.exit(1)
    
    # 创建平台分析器
    analyzer = PlatformAnalyzer(args.config)
    
    # 运行分析
    result = analyzer.run_analysis(args.model_path, args.output)
    
    # 输出结果
    if result["status"] == "success":
        print(f"分析成功，检测到 {result['spaces_count']} 个空间和 {result['openings_count']} 个开口")
        print(f"总耗时: {result['elapsed_time']:.2f}秒")
        if result.get("output_file"):
            print(f"结果已保存到: {result['output_file']}")
    else:
        print(f"分析失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()