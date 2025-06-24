#!/usr/bin/env python3

import sys
import os

sys.path.append("/Users/KC/KCodes/thrasio_iq_backend/services/worker/app")

try:
    from tools.bigquery.query_executor import create_query_executor

    print("✅ 成功导入 create_query_executor")

    executor = create_query_executor("thrasio-dev-data-wh-7ee095")
    print("✅ 成功创建 executor")

    print(f"Logger exists: {hasattr(executor, 'logger')}")
    if hasattr(executor, "logger"):
        print(f"Logger type: {type(executor.logger)}")
        print(f"Logger value: {executor.logger}")
    else:
        print("❌ Logger 不存在")
        print(f"Executor attributes: {dir(executor)}")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()
