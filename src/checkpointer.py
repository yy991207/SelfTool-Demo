"""MongoDB Checkpointer - 会话状态持久化存储"""

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Iterator, Tuple

# 东八区时区
CHINA_TZ = timezone(timedelta(hours=8))
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from .connection_manager import connection_manager


class MongoDBCheckpointer(BaseCheckpointSaver):
    """基于 MongoDB 的 Checkpoint 存储器"""
    
    COLLECTION_NAME = "checkpoints"
    
    def __init__(self):
        super().__init__(serde=JsonPlusSerializer())
    
    def _get_collection(self):
        """获取 checkpoints 集合"""
        return connection_manager.db.get_collection(self.COLLECTION_NAME)
    
    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict,
    ) -> dict:
        """保存 checkpoint"""
        collection = self._get_collection()
        if collection is None:
            return config
        
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
            "checkpoint": self.serde.dumps(checkpoint),
            "metadata": self.serde.dumps(metadata),
            "created_at": datetime.now(CHINA_TZ),
        }
        
        collection.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {"$set": doc},
            upsert=True
        )
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
    
    def put_writes(
        self,
        config: dict,
        writes: list,
        task_id: str,
    ) -> None:
        """保存中间写入（用于断点恢复）"""
        collection = self._get_collection()
        if collection is None:
            return
        
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id", "")
        
        collection.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {
                "$push": {
                    "pending_writes": {
                        "task_id": task_id,
                        "writes": self.serde.dumps(writes),
                    }
                }
            }
        )
    
    async def aget_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """异步获取 checkpoint（调用同步方法）"""
        return self.get_tuple(config)
    
    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict,
    ) -> dict:
        """异步保存 checkpoint"""
        return self.put(config, checkpoint, metadata, new_versions)
    
    async def aput_writes(
        self,
        config: dict,
        writes: list,
        task_id: str,
    ) -> None:
        """异步保存中间写入"""
        return self.put_writes(config, writes, task_id)
    
    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """获取指定的 checkpoint"""
        collection = self._get_collection()
        if collection is None:
            return None
        
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        
        if checkpoint_id:
            doc = collection.find_one({
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            })
        else:
            doc = collection.find_one(
                {"thread_id": thread_id},
                sort=[("created_at", -1)]
            )
        
        if not doc:
            return None
        
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": doc["thread_id"],
                    "checkpoint_id": doc["checkpoint_id"],
                }
            },
            checkpoint=self.serde.loads(doc["checkpoint"]),
            metadata=self.serde.loads(doc["metadata"]),
            parent_config={
                "configurable": {
                    "thread_id": doc["thread_id"],
                    "checkpoint_id": doc["parent_checkpoint_id"],
                }
            } if doc.get("parent_checkpoint_id") else None,
            pending_writes=None,
        )
    
    def list(
        self,
        config: Optional[dict],
        *,
        filter: Optional[dict] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """列出 checkpoints"""
        collection = self._get_collection()
        if collection is None:
            return
        
        query = {}
        if config:
            query["thread_id"] = config["configurable"]["thread_id"]
        
        if before:
            query["created_at"] = {"$lt": before.get("created_at", datetime.utcnow())}
        
        cursor = collection.find(query).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        
        for doc in cursor:
            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": doc["thread_id"],
                        "checkpoint_id": doc["checkpoint_id"],
                    }
                },
                checkpoint=self.serde.loads(doc["checkpoint"]),
                metadata=self.serde.loads(doc["metadata"]),
                parent_config={
                    "configurable": {
                        "thread_id": doc["thread_id"],
                        "checkpoint_id": doc["parent_checkpoint_id"],
                    }
                } if doc.get("parent_checkpoint_id") else None,
                pending_writes=None,
            )
    
    def get_thread_history(self, thread_id: str, limit: int = 10) -> list:
        """获取线程的会话历史"""
        collection = self._get_collection()
        if collection is None:
            return []
        
        docs = list(collection.find(
            {"thread_id": thread_id}
        ).sort("created_at", -1).limit(limit))
        
        history = []
        for doc in docs:
            checkpoint = self.serde.loads(doc["checkpoint"])
            history.append({
                "checkpoint_id": doc["checkpoint_id"],
                "created_at": doc["created_at"],
                "channel_values": checkpoint.get("channel_values", {})
            })
        return history
    
    def list_threads(self) -> list:
        """列出所有会话线程"""
        collection = self._get_collection()
        if collection is None:
            return []
        
        return collection.distinct("thread_id")
    
    def delete_thread(self, thread_id: str) -> bool:
        """删除指定线程的所有 checkpoints"""
        collection = self._get_collection()
        if collection is None:
            return False
        
        result = collection.delete_many({"thread_id": thread_id})
        return result.deleted_count > 0


# 全局 checkpointer 实例
checkpointer = MongoDBCheckpointer()
