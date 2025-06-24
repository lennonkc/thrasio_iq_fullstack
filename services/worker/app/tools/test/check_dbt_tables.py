#!/usr/bin/env python3
"""
快速检查dbt_kc_ai_test数据集中的表

自动化脚本，用于快速列出指定数据集中的所有表
"""

import os
import sys
from typing import List, Dict, Any

# Google Cloud imports
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Forbidden


def check_dbt_tables(project_id: str, dataset_id: str = "dbt_kc_ai_test") -> Dict[str, Any]:
    """
    检查指定数据集中的表
    
    Args:
        project_id: GCP项目ID
        dataset_id: 数据集ID，默认为'dbt_kc_ai_test'
        
    Returns:
        检查结果
    """
    result = {
        "success": False,
        "project_id": project_id,
        "dataset_id": dataset_id,
        "tables": [],
        "table_count": 0,
        "error": None
    }
    
    try:
        # 初始化BigQuery客户端
        client = bigquery.Client(project=project_id)
        print(f"✅ BigQuery客户端连接成功 (项目: {project_id})")
        
        # 检查数据集是否存在
        try:
            dataset_ref = client.dataset(dataset_id)
            dataset = client.get_dataset(dataset_ref)
            print(f"✅ 数据集 '{dataset_id}' 存在")
            print(f"   位置: {dataset.location}")
            print(f"   创建时间: {dataset.created}")
            if dataset.description:
                print(f"   描述: {dataset.description}")
        except NotFound:
            result["error"] = f"数据集 '{dataset_id}' 不存在"
            print(f"❌ {result['error']}")
            return result
        except Forbidden:
            result["error"] = f"没有访问数据集 '{dataset_id}' 的权限"
            print(f"❌ {result['error']}")
            return result
        
        # 列出表
        print(f"\n📋 正在列出数据集 '{dataset_id}' 中的表...")
        tables = list(client.list_tables(dataset_ref))
        
        if not tables:
            print(f"⚠️  数据集 '{dataset_id}' 中没有表")
            result["success"] = True
            return result
        
        # 收集表信息
        table_info = []
        for table in tables:
            try:
                # 获取详细的表信息
                table_ref = client.get_table(table.reference)
                info = {
                    "table_id": table.table_id,
                    "full_table_id": table.full_table_id,
                    "table_type": table.table_type,
                    "num_rows": table_ref.num_rows,
                    "num_bytes": table_ref.num_bytes,
                    "created": table_ref.created.isoformat() if table_ref.created else None,
                    "modified": table_ref.modified.isoformat() if table_ref.modified else None
                }
            except Exception as e:
                # 如果无法获取详细信息，使用基本信息
                print(f"⚠️  无法获取表 '{table.table_id}' 的详细信息: {str(e)}")
                info = {
                    "table_id": table.table_id,
                    "full_table_id": table.full_table_id,
                    "table_type": table.table_type,
                    "num_rows": None,
                    "num_bytes": None,
                    "created": None,
                    "modified": None
                }
            table_info.append(info)
        
        result["tables"] = table_info
        result["table_count"] = len(table_info)
        result["success"] = True
        
        # 打印表信息
        print(f"\n✅ 找到 {len(table_info)} 个表:")
        print("=" * 80)
        
        for i, table in enumerate(table_info, 1):
            print(f"{i:2d}. {table['table_id']}")
            print(f"     类型: {table['table_type']}")
            if table['num_rows'] is not None:
                print(f"     行数: {table['num_rows']:,}")
            if table['num_bytes'] is not None:
                size_mb = table['num_bytes'] / 1024 / 1024
                print(f"     大小: {size_mb:.2f} MB")
            print(f"     完整ID: {table['full_table_id']}")
            if i < len(table_info):
                print()
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ 发生错误: {str(e)}")
        return result


def generate_sample_queries(project_id: str, dataset_id: str, tables: List[Dict[str, Any]]) -> List[str]:
    """
    为表生成示例查询
    
    Args:
        project_id: 项目ID
        dataset_id: 数据集ID
        tables: 表列表
        
    Returns:
        示例查询列表
    """
    queries = []
    
    for table in tables[:5]:  # 只为前5个表生成查询
        table_id = table['table_id']
        full_table_id = f"`{project_id}.{dataset_id}.{table_id}`"
        
        # 基本查询
        basic_query = f"""
-- 查看表 {table_id} 的基本信息
SELECT COUNT(*) as total_rows
FROM {full_table_id};
"""
        
        # 预览查询
        preview_query = f"""
-- 预览表 {table_id} 的前10行
SELECT *
FROM {full_table_id}
LIMIT 10;
"""
        
        queries.extend([basic_query.strip(), preview_query.strip()])
    
    return queries


def main():
    """
    主函数
    """
    print("🔍 dbt_kc_ai_test 数据集表检查工具")
    print("=" * 50)
    
    # 获取项目ID
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    # 如果环境变量未设置，尝试从命令行参数获取
    if not project_id and len(sys.argv) > 1:
        project_id = sys.argv[1]
    
    # 如果仍然没有项目ID，提示用户
    if not project_id:
        print("❌ 未找到GCP项目ID")
        print("\n请使用以下方式之一指定项目ID:")
        print("1. 设置环境变量: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        print("2. 命令行参数: python check_dbt_tables.py your-project-id")
        return
    
    print(f"🎯 检查项目: {project_id}")
    print(f"📊 目标数据集: dbt_kc_ai_test")
    print()
    
    # 检查表
    result = check_dbt_tables(project_id)
    
    if result["success"]:
        if result["table_count"] > 0:
            print(f"\n📝 生成示例查询...")
            queries = generate_sample_queries(
                project_id, 
                result["dataset_id"], 
                result["tables"]
            )
            
            print("\n💡 示例查询 (可复制到BigQuery控制台):")
            print("=" * 60)
            for i, query in enumerate(queries[:4], 1):  # 只显示前4个查询
                print(f"\n-- 查询 {i}:")
                print(query)
            
            if len(queries) > 4:
                print(f"\n... 还有 {len(queries) - 4} 个查询未显示")
        
        print("\n✅ 检查完成")
    else:
        print(f"\n❌ 检查失败: {result['error']}")
        print("\n💡 故障排除建议:")
        print("1. 确认项目ID是否正确")
        print("2. 确认已通过 'gcloud auth application-default login' 认证")
        print("3. 确认账号有访问BigQuery的权限")
        print("4. 确认数据集 'dbt_kc_ai_test' 存在于指定项目中")


if __name__ == "__main__":
    main()