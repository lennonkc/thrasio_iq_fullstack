"""BigQuery查询执行工具测试脚本

该脚本用于测试BigQuery查询执行工具的功能，包括正常查询、错误处理、试运行等场景。
基于Thrasio IQ企业级多Agent系统的BigQuery x Looker数据分析Agent需求开发。
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tools.bigquery.query_executor import BigQueryQueryExecutor, create_query_executor


def test_basic_query():
    """
    测试基本查询功能
    """
    print("\n=== 测试基本查询功能 ===")
    
    # 获取项目ID
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-data-wh-7ee095")
    print(f"使用项目ID: {project_id}")
    
    try:
        # 创建查询执行工具
        executor = create_query_executor(project_id=project_id)
        print("✅ 查询执行工具创建成功")
        
        # 测试查询参数
        table_name = "mart_order_2025"
        query = """
        SELECT * 
        FROM `thrasio-dev-data-wh-7ee095.dbt_kc_ai_test.mart_order_2025` 
        LIMIT 10
        """
        
        print(f"\n📊 执行查询:")
        print(f"表名: {table_name}")
        print(f"查询语句: {query.strip()}")
        
        # 执行查询
        result_json = executor._run(
            table_name=table_name,
            query=query,
            max_results=10,
            timeout=60.0,
            dry_run=False
        )
        
        # 解析结果
        result = json.loads(result_json)
        
        if result["success"]:
            print("\n✅ 查询执行成功!")
            print(f"   返回行数: {result['row_count']}")
            print(f"   列数: {len(result['columns'])}")
            print(f"   列名: {', '.join(result['columns'])}")
            print(f"   处理字节数: {result['bytes_processed']:,} bytes")
            print(f"   执行时间: {result['execution_time']:.2f} 秒")
            
            # 显示前几行数据
            if result['data']:
                print("\n📋 前3行数据:")
                for i, row in enumerate(result['data'][:3]):
                    print(f"   行 {i+1}: {row}")
        else:
            print("\n❌ 查询执行失败!")
            print(f"   错误信息: {result['error_message']}")
            
        return result["success"]
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False


def test_dry_run():
    """
    测试试运行功能
    """
    print("\n=== 测试试运行功能 ===")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-data-wh-7ee095")
    
    try:
        executor = create_query_executor(project_id=project_id)
        
        table_name = "mart_order_2025"
        query = """
        SELECT * 
        FROM `thrasio-dev-data-wh-7ee095.dbt_kc_ai_test.mart_order_2025` 
        LIMIT 5
        """
        
        print(f"\n🔍 执行试运行:")
        print(f"表名: {table_name}")
        
        # 执行试运行
        result_json = executor._run(
            table_name=table_name,
            query=query,
            timeout=60.0,
            dry_run=True
        )
        
        result = json.loads(result_json)
        
        if result["success"]:
            print("\n✅ 试运行成功!")
            print(f"   预计处理字节数: {result['bytes_processed']:,} bytes")
            print(f"   执行时间: {result['execution_time']:.2f} 秒")
            print(f"   返回行数: {result['row_count']} (试运行为0)")
        else:
            print("\n❌ 试运行失败!")
            print(f"   错误信息: {result['error_message']}")
            
        return result["success"]
        
    except Exception as e:
        print(f"\n❌ 试运行测试失败: {str(e)}")
        return False


def test_invalid_query():
    """
    测试无效查询的错误处理
    """
    print("\n=== 测试无效查询错误处理 ===")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-data-wh-7ee095")
    
    try:
        executor = create_query_executor(project_id=project_id)
        
        table_name = "nonexistent_table"
        query = """
        SELECT * 
        FROM `thrasio-dev-data-wh-7ee095.dbt_kc_ai_test.nonexistent_table` 
        LIMIT 10
        """
        
        print(f"\n❌ 执行无效查询 (预期失败):")
        print(f"表名: {table_name}")
        
        # 执行无效查询
        result_json = executor._run(
            table_name=table_name,
            query=query,
            max_results=10,
            timeout=60.0,
            dry_run=False
        )
        
        result = json.loads(result_json)
        
        if not result["success"]:
            print("\n✅ 错误处理正常!")
            print(f"   错误信息: {result['error_message']}")
            print(f"   执行时间: {result['execution_time']:.2f} 秒")
            return True
        else:
            print("\n❌ 预期失败但查询成功了!")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误处理测试失败: {str(e)}")
        return False


def test_query_validation():
    """
    测试查询验证功能
    """
    print("\n=== 测试查询验证功能 ===")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-data-wh-7ee095")
    
    try:
        executor = create_query_executor(project_id=project_id)
        
        # 测试安全查询
        safe_query = "SELECT * FROM table LIMIT 10"
        is_safe = executor.validate_query(safe_query, "test_table")
        print(f"\n✅ 安全查询验证: {is_safe} (预期: True)")
        
        # 测试危险查询
        dangerous_queries = [
            "DROP TABLE test_table",
            "DELETE FROM test_table",
            "INSERT INTO test_table VALUES (1, 2)",
            "UPDATE test_table SET col1 = 'value'"
        ]
        
        for dangerous_query in dangerous_queries:
            is_safe = executor.validate_query(dangerous_query, "test_table")
            print(f"❌ 危险查询验证: {is_safe} (预期: False) - {dangerous_query[:20]}...")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 查询验证测试失败: {str(e)}")
        return False


async def test_async_query():
    """
    测试异步查询功能
    """
    print("\n=== 测试异步查询功能 ===")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-data-wh-7ee095")
    
    try:
        executor = create_query_executor(project_id=project_id)
        
        table_name = "mart_order_2025"
        query = """
        SELECT * 
        FROM `thrasio-dev-data-wh-7ee095.dbt_kc_ai_test.mart_order_2025` 
        LIMIT 5
        """
        
        print(f"\n🔄 执行异步查询:")
        print(f"表名: {table_name}")
        
        # 执行异步查询
        result_json = await executor._arun(
            table_name=table_name,
            query=query,
            max_results=5,
            timeout=60.0,
            dry_run=False
        )
        
        result = json.loads(result_json)
        
        if result["success"]:
            print("\n✅ 异步查询执行成功!")
            print(f"   返回行数: {result['row_count']}")
            print(f"   执行时间: {result['execution_time']:.2f} 秒")
        else:
            print("\n❌ 异步查询执行失败!")
            print(f"   错误信息: {result['error_message']}")
            
        return result["success"]
        
    except Exception as e:
        print(f"\n❌ 异步查询测试失败: {str(e)}")
        return False


def main():
    """
    运行所有测试
    """
    print("🚀 开始BigQuery查询执行工具测试")
    print("=" * 50)
    
    # 检查环境变量
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("⚠️  警告: 未设置GOOGLE_CLOUD_PROJECT环境变量，使用默认项目ID")
    
    test_results = []
    
    # 运行同步测试
    test_results.append(("基本查询功能", test_basic_query()))
    test_results.append(("试运行功能", test_dry_run()))
    test_results.append(("无效查询错误处理", test_invalid_query()))
    test_results.append(("查询验证功能", test_query_validation()))
    
    # 运行异步测试
    try:
        async_result = asyncio.run(test_async_query())
        test_results.append(("异步查询功能", async_result))
    except Exception as e:
        print(f"\n❌ 异步测试运行失败: {str(e)}")
        test_results.append(("异步查询功能", False))
    
    # 输出测试结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过! BigQuery查询执行工具工作正常。")
        return True
    else:
        print("⚠️  部分测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)