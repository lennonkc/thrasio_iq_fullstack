"""外部记忆存储管理"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class ExternalMemory:
    """外部记忆存储管理器"""

    def __init__(self, storage_dir: str = "app/memory/storage"):
        """初始化外部记忆存储

        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        logger.info("外部记忆存储初始化", storage_dir=storage_dir)

    def store_analysis_result(self, session_id: str, data: Dict[str, Any]) -> str:
        """存储分析结果到外部记忆

        Args:
            session_id: 会话ID
            data: 要存储的数据

        Returns:
            存储键值
        """
        memory_key = f"{session_id}_{uuid.uuid4().hex[:8]}"
        file_path = os.path.join(self.storage_dir, f"{memory_key}.json")

        storage_data = {
            "session_id": session_id,
            "memory_key": memory_key,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)

            logger.info("分析结果已存储到外部记忆", memory_key=memory_key)
            return memory_key

        except Exception as e:
            logger.error("存储分析结果失败", error=str(e), memory_key=memory_key)
            raise

    def retrieve_analysis_result(self, memory_key: str) -> Optional[Dict[str, Any]]:
        """从外部记忆检索分析结果

        Args:
            memory_key: 存储键值

        Returns:
            检索到的数据，如果不存在则返回None
        """
        file_path = os.path.join(self.storage_dir, f"{memory_key}.json")

        if not os.path.exists(file_path):
            logger.warning("外部记忆文件不存在", memory_key=memory_key)
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                storage_data = json.load(f)

            logger.info("从外部记忆检索数据成功", memory_key=memory_key)
            return storage_data["data"]

        except Exception as e:
            logger.error("检索外部记忆失败", error=str(e), memory_key=memory_key)
            return None

    def list_session_memories(self, session_id: str) -> List[str]:
        """列出会话的所有记忆键值

        Args:
            session_id: 会话ID

        Returns:
            记忆键值列表
        """
        memory_keys = []

        try:
            for filename in os.listdir(self.storage_dir):
                if filename.startswith(f"{session_id}_") and filename.endswith(".json"):
                    memory_key = filename[:-5]  # 移除.json后缀
                    memory_keys.append(memory_key)

            logger.info("列出会话记忆", session_id=session_id, count=len(memory_keys))
            return memory_keys

        except Exception as e:
            logger.error("列出会话记忆失败", error=str(e), session_id=session_id)
            return []

    def cleanup_old_memories(self, days_old: int = 7) -> int:
        """清理过期的记忆文件

        Args:
            days_old: 保留天数

        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)

        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.storage_dir, filename)
                    file_time = os.path.getmtime(file_path)

                    if file_time < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1

            logger.info(
                "清理过期记忆完成", cleaned_count=cleaned_count, days_old=days_old
            )
            return cleaned_count

        except Exception as e:
            logger.error("清理过期记忆失败", error=str(e))
            return 0

    def store_large_result(
        self, session_id: str, result_data: Any, summary: str
    ) -> str:
        """存储大型结果数据，用于token限制场景

        Args:
            session_id: 会话ID
            result_data: 大型结果数据
            summary: 数据摘要

        Returns:
            存储键值
        """
        data = {
            "type": "large_result",
            "summary": summary,
            "full_data": result_data,
            "size": len(str(result_data)),
        }

        return self.store_analysis_result(session_id, data)
