-- ==========================================================
-- 垂域大模型问答系统 (RAG) - 数据库初始化脚本（教学版）
-- 请按顺序执行
-- ==========================================================
-- 0. 创建数据库
CREATE DATABASE domain_knowledge_db;
-- 1. 启用 PGVector 核心扩展（没这个做不了向量相似度计算）
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- ==========================================================
-- 2. 核心向量知识库表（LlamaIndex 默认识别的表结构）
-- 这张表用来存储解析好的 PDF/TXT/MD 文本块（Chunk）及其向量
-- 表名规则：data_ + config.TABLE_NAME
-- 你的 TABLE_NAME=knowledge_llama_index，因此实际表名是 data_knowledge_llama_index
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.data_knowledge_llama_index (
    id bigserial PRIMARY KEY,                 -- 自增主键
    text character varying NOT NULL,          -- 文本切片内容 (Chunk)
    metadata_ json,                           -- 元数据（文件名、页码、OCR 信息等）
    node_id character varying,                -- LlamaIndex 自动生成的节点ID
    embedding public.vector(384)              -- 向量字段：384维（bge-base-zh-v1.5）
);

-- ==========================================================
-- 3. 语义缓存表（用于缓存问答结果，减少重复推理）
-- 注意：表名必须与代码中的 semantic_cache.py 保持一致
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.semantic_cache (
    id serial PRIMARY KEY,
    question text NOT NULL,                       -- 用户提问原文
    answer text NOT NULL,                         -- 大模型回答
    source character varying(50) DEFAULT 'rag',   -- 来源标识 (rag / web / llm / cache)
    question_embedding public.vector(384),        -- 问题向量（384维）
    use_search boolean DEFAULT false,             -- 该回答是否启用了联网搜索
    hit_count integer DEFAULT 0,                  -- 缓存命中次数
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- 4. 创建向量索引（提升缓存检索速度）
-- ==========================================================
-- 针对语义缓存问题向量创建 IVFFlat 索引 (ANN)
-- vector_cosine_ops：余弦相似度
-- lists=100：聚类中心数（教学环境够用，数据特别大可再调优）
CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
ON public.semantic_cache
USING ivfflat (question_embedding public.vector_cosine_ops)
WITH (lists = '100');

-- ==========================================================
-- 说明
-- 1) 当前教学脚本不再创建 knowledge / qa_cache（历史遗留，不参与本项目主流程）
-- 2) data_knowledge_llama_index 暂不建索引：小数据量时顺序扫描更简单直观
--    若后期数据量很大（如10万+切片），可再补 ivfflat/hnsw 索引
-- ==========================================================