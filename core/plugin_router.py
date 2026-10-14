from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class PluginRouter:
    """
    Векторный поиск плагинов по описанию действий.
    
    Использует ChromaDB для хранения эмбеддингов и семантического поиска.
    При регистрации плагина создаёт эмбеддинг его описания и списка действий.
    При поиске находит наиболее похожий плагин по косинусному сходству.
    """
    
    def __init__(self, db_path: str = "data/plugins_cache"):
        """
        Инициализирует PluginRouter.
        
        Args:
            db_path: Путь к директории ChromaDB
        """
        
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.client = Client(Settings(
            persist_directory=db_path,
            anonymized_telemetry=False
        ))
        
        # Коллекция с эмбеддингами плагинов
        self.collection = self.client.get_or_create_collection(
            name="plugins",
            metadata={"hnsw:space": "cosine"}  # Косинусное сходство
        )
        
        logger.info(f"✅ PluginRouter инициализирован. Плагинов в базе: {self.collection.count()}")
    
    def add_plugin(self, plugin_name: str, description: str, actions: list[str]):
        """
        Добавляет плагин в векторную базу.
        
        Args:
            plugin_name: Уникальное имя плагина (например, "smart_home")
            description: Общее описание плагина
            actions: Список действий, которые поддерживает плагин
                     (например, ["включить свет", "выключить свет"])
        """
        text = f"{description}. Действия: {', '.join(actions)}"
        
        embedding = self.embedder.encode(text).tolist()
        
        self.collection.add(
            ids=[plugin_name],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "name": plugin_name,
                "actions": ", ".join(actions)
            }]
        )
        
        logger.info(f"📦 Плагин '{plugin_name}' добавлен в векторную БД")
    
    def find_plugin(self, action: str, threshold: float = 0.7) -> tuple[str | None, float]:
        """
        Ищет плагин по описанию действия.
        
        Args:
            action: Описание действия (например, "зажги лампу в гостиной")
            threshold: Минимальный порог сходства (0.0 - 1.0)
        
        Returns:
            (plugin_name, similarity) или (None, 0.0) если не найдено
        """
        # Превращаем запрос в вектор
        query_embedding = self.embedder.encode(action).tolist()
        
        # Ищем ближайший плагин
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        
        if results['ids'][0]:
            plugin_name = results['ids'][0][0]
            distance = results['distances'][0][0]
            # ChromaDB с cosine space возвращает distance = 1 - similarity
            similarity = 1 - distance
            
            if similarity >= threshold:
                logger.info(f"🔍 Найден плагин '{plugin_name}' (similarity: {similarity:.2f}) для действия: {action}")
                return plugin_name, similarity
            else:
                logger.warning(f"⚠️ Плагин найден, но similarity слишком низкий: {similarity:.2f}")
        
        return None, 0.0
    
    def remove_plugin(self, plugin_name: str):
        """Удаляет плагин из векторной базы."""
        try:
            self.collection.delete(ids=[plugin_name])
            logger.info(f"🗑️ Плагин '{plugin_name}' удален из векторной БД")
        except Exception as e:
            logger.error(f"Ошибка удаления плагина {plugin_name}: {e}")