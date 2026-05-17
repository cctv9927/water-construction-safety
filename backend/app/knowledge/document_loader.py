"""文档加载与分块模块"""
import os
import re
import logging
from typing import List, Optional, Tuple
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# 尝试导入 PDF 解析库
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyMuPDF not available for PDF parsing")


class DocumentLoader:
    """文档加载器"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        初始化文档加载器

        Args:
            chunk_size: 分块大小（字符数）
            overlap: 块间重叠字符数
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load_text(self, text: str, title: str, source: str,
                  category: str = "通用") -> "Document":
        """从文本创建文档"""
        from .models import Document
        return Document(
            id=str(uuid.uuid4()),
            content=text,
            title=title,
            source=source,
            category=category
        )

    def load_file(self, file_path: str, title: Optional[str] = None,
                  source: Optional[str] = None,
                  category: str = "通用") -> List["Document"]:
        """
        加载文件并分块

        Args:
            file_path: 文件路径
            title: 文档标题（默认使用文件名）
            source: 来源（默认使用文件名）
            category: 分类

        Returns:
            分块后的文档列表
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()

        # 根据文件类型选择加载方法
        if ext in [".txt", ".md"]:
            content = self._load_text_file(file_path)
        elif ext == ".pdf":
            content = self._load_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # 使用文件名作为标题和来源
        title = title or file_path.stem
        source = source or file_path.name

        # 分块
        chunks = self.chunk_text(content)
        documents = []
        for i, chunk in enumerate(chunks):
            from .models import Document
            documents.append(Document(
                id=f"{file_path.stem}_{i}_{uuid.uuid4().hex[:8]}",
                content=chunk,
                title=title,
                source=source,
                category=category
            ))

        return documents

    def _load_text_file(self, file_path: Path) -> str:
        """加载文本文件"""
        encodings = ["utf-8", "gbk", "gb2312", "gb18030"]
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        # 最后尝试二进制读取并解码
        return file_path.read_bytes().decode("utf-8", errors="ignore")

    def _load_pdf(self, file_path: Path) -> str:
        """加载 PDF 文件"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF parsing requires PyMuPDF: pip install pymupdf")

        text_parts = []
        doc = fitz.open(str(file_path))

        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- 第 {page_num + 1} 页 ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts)

    def chunk_text(self, text: str, chunk_size: Optional[int] = None,
                   overlap: Optional[int] = None) -> List[str]:
        """
        滑动窗口分块

        Args:
            text: 待分块文本
            chunk_size: 块大小（默认使用实例配置）
            overlap: 重叠大小（默认使用实例配置）

        Returns:
            分块列表
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.overlap

        if not text or len(text) <= chunk_size:
            return [text] if text else []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size

            # 尝试在句子边界处切分
            if end < text_len:
                # 向前查找最后一个句号、换行或逗号
                chunk = text[start:end]
                last_break = self._find_best_break(chunk)
                if last_break > chunk_size // 2:
                    end = start + last_break
                    chunk = text[start:end]
                else:
                    chunk = text[start:end].strip()

                # 避免块太小
                if len(chunk) < chunk_size // 4 and chunks:
                    # 与上一个块合并
                    chunks[-1] += chunk
                    start = end
                    continue
            else:
                chunk = text[start:].strip()

            if chunk:
                chunks.append(chunk)

            # 滑动窗口
            start = end - overlap
            if start <= chunks[-1].find(chunk) + len(chunk) - overlap:
                start = len("".join(chunks[:-1])) + chunks[-1].find(chunk) + len(chunks[-1]) - overlap

        return chunks

    def _find_best_break(self, text: str) -> int:
        """查找最佳断点（句子边界）"""
        # 优先查找换行
        for sep in ["\n\n", "\n", "。", "！", "？", "；", "，"]:
            pos = text.rfind(sep)
            if pos != -1:
                return pos + len(sep)
        return len(text)

    def add_to_store(self, chunks: List["Document"], vector_store) -> bool:
        """
        将分块文档存入向量存储

        Args:
            chunks: 分块后的文档列表
            vector_store: 向量存储实例

        Returns:
            是否成功
        """
        if not chunks:
            return True

        try:
            return vector_store.upsert(chunks)
        except Exception as e:
            logger.error(f"Failed to add documents to store: {e}")
            return False


# 全局加载器实例
_default_loader: Optional[DocumentLoader] = None


def get_loader(chunk_size: int = 500, overlap: int = 50) -> DocumentLoader:
    """获取全局文档加载器"""
    global _default_loader
    if _default_loader is None:
        _default_loader = DocumentLoader(chunk_size, overlap)
    return _default_loader


def load_and_chunk(text: str, title: str, source: str, category: str = "通用",
                   chunk_size: int = 500, overlap: int = 50) -> List["Document"]:
    """便捷函数：加载文本并分块"""
    loader = DocumentLoader(chunk_size, overlap)
    chunks = loader.chunk_text(text)
    from .models import Document
    return [
        Document(
            id=str(uuid.uuid4()),
            content=chunk,
            title=title,
            source=source,
            category=category
        )
        for chunk in chunks
    ]
