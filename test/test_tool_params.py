#!/usr/bin/env python
"""
测试工具参数解析功能的脚本
"""
import json
import logging
import asyncio
import sys

# 设置日志级别
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-script")

async def test_params_parsing():
    """测试参数解析功能"""
    # 模拟从MCP客户端接收到的参数
    test_cases = [
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
        {
            "tool_name": "broadcast_title",
            "title": "直接参数",
            "subtitle": "直接副标题"
        },
        {
            "tool_name": "broadcast_title",
            "kwargs": '{"title":"JSON字符串参数","subtitle":"JSON副标题"}'
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"测试用例 {i+1}:")
        logger.info(f"原始参数: {test_case}")
        
        # 模拟参数解析逻辑
        actual_kwargs = {}
        if 'kwargs' in test_case and isinstance(test_case['kwargs'], str):
            try:
                # 记录原始的kwargs字符串
                logger.debug(f"收到kwargs字符串: {test_case['kwargs']}")
                logger.debug(f"kwargs类型: {type(test_case['kwargs'])}")
                
                # 尝试解析kwargs字符串为字典
                parsed_kwargs = json.loads(test_case['kwargs'])
                logger.debug(f"解析后的kwargs: {parsed_kwargs}")
                logger.debug(f"解析后的kwargs类型: {type(parsed_kwargs)}")
                
                if isinstance(parsed_kwargs, dict):
                    # 将解析后的参数添加到actual_kwargs
                    actual_kwargs.update(parsed_kwargs)
                    logger.debug(f"已将解析后的kwargs添加到actual_kwargs")
                else:
                    logger.warning(f"解析后的kwargs不是字典: {parsed_kwargs}")
                    # 如果不是字典，保留原始kwargs
                    actual_kwargs['kwargs'] = test_case['kwargs']
                
                # 保留其他参数
                for k, v in test_case.items():
                    if k != 'kwargs' and k != 'tool_name':
                        actual_kwargs[k] = v
                        logger.debug(f"添加其他参数: {k}={v}")
            except json.JSONDecodeError as e:
                # 如果解析失败，记录错误并保留原始kwargs
                logger.warning(f"无法解析kwargs字符串: {test_case['kwargs']}, 错误: {e}")
                actual_kwargs = {k: v for k, v in test_case.items() if k != 'tool_name'}
        else:
            # 如果没有特殊的kwargs参数，直接使用传入的参数
            actual_kwargs = {k: v for k, v in test_case.items() if k != 'tool_name'}
            logger.debug(f"没有找到kwargs参数，使用原始参数")
        
        # 执行工具前，移除kwargs参数，避免传递给不接受它的工具
        if 'kwargs' in actual_kwargs:
            logger.debug(f"从actual_kwargs中移除kwargs参数")
            actual_kwargs.pop('kwargs')
        
        # 记录最终参数
        logger.info(f"最终参数: {actual_kwargs}")
        logger.info("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_params_parsing()) 