#!/usr/bin/env python
"""
测试MCP客户端参数解析的脚本
"""
import json
import logging
import asyncio
import sys

# 设置日志级别
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-script")

async def test_mcp_params_parsing():
    """测试MCP客户端参数解析功能"""
    # 模拟从MCP客户端接收到的参数
    test_cases = [
        # 测试用例1: 标准MCP客户端调用格式
        {
            "tool_name": "broadcast_title",
            "kwargs": json.dumps({
                "title": "主标题",
                "subtitle": "副标题",
                "fade_in": 10,
                "stay": 70,
                "fade_out": 20
            })
        },
        # 测试用例2: 不提供kwargs参数
        {
            "tool_name": "broadcast_title"
        },
        # 测试用例3: 提供无效的JSON字符串
        {
            "tool_name": "broadcast_title",
            "kwargs": "这不是有效的JSON"
        },
        # 测试用例4: 提供非对象的JSON
        {
            "tool_name": "broadcast_title",
            "kwargs": json.dumps(["这是一个数组，不是对象"])
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"测试用例 {i+1}:")
        logger.info(f"原始参数: {test_case}")
        
        # 提取tool_name和kwargs
        tool_name = test_case.get("tool_name")
        kwargs = test_case.get("kwargs")
        
        logger.info(f"工具名称: {tool_name}")
        logger.info(f"kwargs参数: {kwargs}")
        
        # 模拟参数解析逻辑
        actual_kwargs = {}
        
        # 如果提供了kwargs参数，尝试解析为JSON
        if kwargs:
            try:
                # 解析JSON字符串
                parsed_kwargs = json.loads(kwargs)
                logger.info(f"解析后的参数: {parsed_kwargs}")
                
                if isinstance(parsed_kwargs, dict):
                    actual_kwargs = parsed_kwargs
                else:
                    logger.warning(f"解析后的参数不是字典: {parsed_kwargs}")
                    logger.info("返回错误: kwargs 必须是一个有效的JSON对象字符串")
                    continue
            except json.JSONDecodeError as e:
                logger.warning(f"无法解析kwargs字符串: {e}")
                logger.info(f"返回错误: 无法解析kwargs参数: {str(e)}")
                continue
        
        # 记录最终参数
        logger.info(f"最终参数: {actual_kwargs}")
        logger.info("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_mcp_params_parsing()) 