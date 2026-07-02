"""
Servicio RAG - Búsqueda inteligente de productos (Optimización de costos)
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Optimización de costos: solo busca productos relevantes"""
    
    SPANISH_STOPWORDS = {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'de', 'en', 'a', 
        'para', 'por', 'con', 'sin', 'sobre', 'entre', 'hasta', 'desde', 'durante', 'según', 
        'mediante', 'contra', 'del', 'al', 'es', 'son', 'fue', 'fueron', 'ser', 'está', 'estás',
        'estamos', 'estáis', 'están', 'estoy', 'me', 'te', 'se', 'nos', 'os', 'le', 'les',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'que', 'quien', 'cual', 'donde', 'cuando',
        'cuanto', 'como', 'si', 'no', 'ni', 'lo', 'mas', 'pero', 'sino', 'tambien', 'muy'
    }
    
    async def extract_keywords(self, message: str) -> List[str]:
        """Extraer palabras clave del mensaje"""
        words = re.findall(r'\b\w+\b', message.lower())
        keywords = [w for w in words if w not in self.SPANISH_STOPWORDS and len(w) > 2]
        return list(dict.fromkeys(keywords[:10]))  # Máximo 10 palabras clave únicas
    
    async def search_products_simple(self, db, tenant_id: str, message: str) -> List[Dict]:
        """Búsqueda simple de productos (LIKE SQL)"""
        from sqlalchemy import select, or_
        from app.models import Product
        
        try:
            keywords = await self.extract_keywords(message)
            if not keywords:
                return []
            
            # Construir condición OR para búsqueda
            search_conditions = [
                Product.name.ilike(f"%{kw}%") 
                for kw in keywords
            ]
            search_conditions.extend([
                Product.description.ilike(f"%{kw}%") 
                for kw in keywords
            ])
            
            stmt = select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,
                or_(*search_conditions)
            ).limit(8)
            
            result = await db.execute(stmt)
            products = result.scalars().all()
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "price": float(p.price),
                    "image_url": p.image_url,
                    "stock": p.stock,
                    "attributes": p.attributes
                }
                for p in products
            ]
        except Exception as e:
            logger.error(f"Error buscando productos: {str(e)}")
            return []
    
    def format_products_for_prompt(self, products: List[Dict], max_chars: int = 1000) -> str:
        """Formatear productos para inyectar en el prompt (optimizado)"""
        if not products:
            return "📦 No se encontraron productos relacionados."
        
        lines = ["📦 **Productos disponibles:**"]
        char_count = 0
        
        for p in products:
            stock_text = "✅ En stock" if p["stock"] > 0 else "❌ Agotado"
            line = f"• *{p['name']}* - ${p['price']:.2f} ({stock_text})"
            
            if char_count + len(line) > max_chars:
                break
            
            lines.append(line)
            char_count += len(line)
        
        return "\n".join(lines)


rag_service = RAGService()
