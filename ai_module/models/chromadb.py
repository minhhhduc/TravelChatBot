"""ChromaDB vector database manager for TravelChatBot storage and retrieval.

This module provides the ChromaDBManager class for managing recipe data
in a vector database, including document storage, semantic search, and
RAG (Retrieval-Augmented Generation) context preparation.

Author: TravelChatBot Team
Version: 2.0.0
"""
import chromadb
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

from . import config

class ChromaDBManager:
    """Manages ChromaDB interactions for TravelChatBot storage and retrieval.
    
    This class handles all operations with the ChromaDB vector database,
    including recipe data loading, document embedding, semantic search,
    and context preparation for RAG applications.
    
    Attributes:
        client: ChromaDB persistent client instance
        _collections: Cache of ChromaDB collections
        recipes: List of loaded recipe dictionaries
        set_of_nuts: Dictionary of nutrition keys and their units
        
    Example:
        >>> manager = ChromaDBManager(
        ...     db_path="./chroma_db",
        ...     json_path="./recipes.json"
        ... )
        >>> manager.add_recipes_to_collection("recipes")
        >>> results = manager.search("recipes", "pasta with tomatoes", n_results=5)
    """

    def __init__(self, db_path: str = "./data.db", json_path: Optional[str] = None):
        """Initializes the ChromaDB client and loads recipe data.
        
        Sets up the persistent ChromaDB client, initializes collection cache,
        and optionally loads recipe data from a JSON file.
        
        Args:
            db_path: Path to the directory for the persistent database.
                Defaults to "./data.db".
            json_path: Path to the JSON file containing recipe data.
                If None, no recipes are loaded initially.
                
        Raises:
            IOError: If the database path is not accessible.
            json.JSONDecodeError: If the JSON file is malformed.
            
        Example:
            >>> manager = ChromaDBManager(
            ...     db_path="./my_recipes_db",
            ...     json_path="./recipe_data.json"
            ... )
        """
        print(f"INFO: Initializing ChromaDBManager with DB path: '{db_path}'")
        self.client = chromadb.PersistentClient(path=db_path)
        self._collections: Dict[str, chromadb.Collection] = {}
        self.json_path = json_path
        
        # Loaded items from json/jsonl. Name kept for backward-compat.
        # Keep this lazy so normal chat queries do not read the full dataset.
        self.recipes: List[Dict[str, Any]] = []
        
        self.set_of_nuts = self._extract_nutrition_keys()
        print("INFO: ChromaDBManager ready.")

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Retrieves a collection from cache or creates it if it doesn't exist.
        
        This method implements caching for ChromaDB collections to avoid
        repeated database calls. Collections are created with default settings.
        
        Args:
            name: The name of the collection to retrieve or create.
            
        Returns:
            The ChromaDB collection object.
            
        Example:
            >>> collection = manager.get_or_create_collection("recipes")
            >>> print(f"Collection has {collection.count()} documents")
        """
        if name not in self._collections:
            print(f"INFO: Accessing collection '{name}' for the first time...")
            self._collections[name] = self.client.get_or_create_collection(name=name, configuration={
                "hnsw:space": "cosine",
                "hnsw:ef_construction": 200,
                "hnsw:M": 16,
            })
        return self._collections[name]

    def load_recipes_from_json(self, json_path: str) -> int:
        """Loads recipe data from a JSON file into memory.
        
        Reads and parses a JSON file containing recipe data, storing it
        in the recipes attribute for later processing.
        
        Args:
            json_path: The path to the JSON file containing recipe data.
                Expected format: List of recipe dictionaries.
                
        Returns:
            The number of recipes successfully loaded.
            
        Raises:
            IOError: If the file cannot be read.
            json.JSONDecodeError: If the JSON is malformed.
            
        Example:
            >>> count = manager.load_recipes_from_json("recipes.json")
            >>> print(f"Loaded {count} recipes")
        """
        try:
            json_file = Path(json_path)
            if not json_file.exists():
                print(f"ERROR: JSON file not found at: {json_path}")
                return 0
            
            with json_file.open('r', encoding='utf-8') as f:
                if str(json_path).endswith('.jsonl'):
                    self.recipes = []
                    for line in f:
                        line = line.strip()
                        if line:
                            self.recipes.append(json.loads(line))
                else:
                    self.recipes = json.load(f)
            
            print(f"INFO: Loaded {len(self.recipes)} items from {json_path}")
            return len(self.recipes)
        except Exception as e:
            print(f"ERROR: Failed to load or parse data file: {e}")
            return 0

    def _format_recipe_content(self, recipe: Dict[str, Any]) -> str:
        """Formats a recipe dictionary into a searchable text string.
        
        Converts structured recipe data into a formatted text representation
        optimized for vector embedding and semantic search.
        
        Args:
            recipe: Dictionary containing recipe data with keys like
                'Summary', 'Ingredients', 'Instructions', 'Metadata'.
                
        Returns:
            A formatted string representation of the recipe suitable
            for embedding. Format: "Summary: ... | Ingredients: ... | 
            Instructions: ... | Prep: ...min, Cook: ...min"
            
        Example:
            >>> recipe = {
            ...     "Summary": "Delicious pasta dish",
            ...     "Ingredients": ["pasta", "tomato sauce"],
            ...     "Instructions": ["Boil pasta", "Add sauce"]
            ... }
            >>> formatted = manager._format_recipe_content(recipe)
        """
        parts = []
        if "Summary" in recipe:
            parts.append(f"Summary: {recipe['Summary']}")
        
        if "Ingredients" in recipe:
            parts.append("Ingredients: " + ", ".join(recipe['Ingredients']))
        
        if "Instructions" in recipe:
            parts.append("Instructions: " + " ".join(recipe['Instructions']))
        
        if "Metadata" in recipe and isinstance(recipe["Metadata"], dict):
            meta = recipe["Metadata"]
            parts.append(f"Prep: {meta.get('prep_time_minutes', 'N/A')}min, Cook: {meta.get('cook_time_minutes', 'N/A')}min")
        
        return " | ".join(parts)
    
    def _extract_nutrition_keys(self) -> Dict[str, str]:
        """Extracts unique nutrition keys and their units from loaded recipes.
        
        Scans through all loaded recipe data to collect all unique nutrition
        parameter names (e.g., 'calories', 'protein', 'fat') and their
        corresponding units (e.g., 'kcal', 'g', 'mg').
        
        This information is used to create dynamic nutrition filtering
        schemas and validate nutrition-based queries.
        
        Returns:
            Dictionary mapping nutrition parameter names to their units.
            Keys are nutrition names like 'calories', 'protein'.
            Values are unit strings like 'kcal', 'g', 'mg'.
            
        Example:
            >>> manager._extract_nutrition_keys()
            # {'calories': 'kcal', 'protein': 'g', 'sodium': 'mg', ...}
        """
        nutrition_keys = {}
        for recipe in self.recipes:
            for nut, details in recipe.get("Nutrition", {}).items():
                if nut not in nutrition_keys:
                    nutrition_keys[nut] = details.get('unit', '')
        return nutrition_keys
    
    def _sort_results(
        self, 
        results: Dict[str, Any], 
        sort_by: str, 
        sort_order: str = "asc",
        limit: int = 10
    ) -> List[int]:
        """Sorts ChromaDB search results by a metadata field value.
        
        Takes the results from a ChromaDB query and sorts them based on
        a specified metadata field (typically nutrition values). This enables
        queries like "lowest calorie dishes" or "highest protein recipes".
        
        Args:
            results: ChromaDB query results containing documents, metadatas,
                and distances from vector search.
            sort_by: Metadata field name to sort by. Usually nutrition fields
                like 'nutr_val_calories', 'nutr_val_protein'.
            sort_order: Sort direction. 'asc' for ascending (lowest first),
                'desc' for descending (highest first). Defaults to 'asc'.
            limit: Maximum number of sorted results to return.
                
        Returns:
            List of indices representing the sorted order of results.
            These indices can be used to reorder the original results.
            
        Example:
            >>> # Sort by calories (ascending = lowest first)
            >>> sorted_indices = manager._sort_results(
            ...     results, 'nutr_val_calories', 'asc', 10
            ... )
            >>> # Returns [3, 7, 1, 9, ...] representing result order
        """
        metadatas = results['metadatas'][0]
        
        # Create list of (index, value) tuples
        indexed_values = []
        for i, metadata in enumerate(metadatas):
            value = metadata.get(sort_by)
            if value is None:
                if sort_by == 'time':
                    value = "0000-00-00" if sort_order == "desc" else "9999-99-99"
                else:
                    value = float('-inf') if sort_order == "desc" else float('inf')
            indexed_values.append((i, value))
        
        # Sort by value
        reverse = (sort_order == 'desc')
        indexed_values.sort(key=lambda x: x[1], reverse=reverse)
        
        # Return only the indices, limited to the specified number
        return [idx for idx, _ in indexed_values[:limit]]

    def add_recipes_to_collection(self, collection_name: str = "recipes", batch_size: int = 100) -> int:
        """Adds all loaded items to a ChromaDB collection in batches.
        
        Processes the loaded recipe data and stores it in ChromaDB for vector search.
        Each recipe is converted to a searchable text format and stored with
        comprehensive metadata including nutrition values, cooking times, and URLs.
        
        Processing includes:
            - Text formatting for embedding (summary, ingredients, instructions)
            - Metadata extraction (prep time, cook time, servings, nutrition)
            - Batch processing for memory efficiency
            - Error handling for malformed recipes
            
        Args:
            collection_name: Name of the ChromaDB collection to store recipes in.
                Defaults to "recipes".
            batch_size: Number of recipes to process in each batch.
                Larger batches are more efficient but use more memory.
                Defaults to 100.
                
        Returns:
            Total number of new recipes successfully added to the collection.
            
        Raises:
            Exception: If ChromaDB operations fail (logged but not raised).
            
        Example:
            >>> manager.load_recipes_from_json("recipes.json")
            >>> count = manager.add_recipes_to_collection("my_recipes", 50)
            >>> print(f"Added {count} recipes to ChromaDB")
        """
        if not self.recipes and self.json_path:
            self.load_recipes_from_json(self.json_path)

        if not self.recipes:
            print("WARNING: No items loaded to add to the collection.")
            return 0
        
        collection = self.get_or_create_collection(name=collection_name)
        total_added = 0
        
        for i in range(0, len(self.recipes), batch_size):
            batch = self.recipes[i:i + batch_size]
            print(f"INFO: Processing batch {i // batch_size + 1}/{(len(self.recipes) + batch_size - 1) // batch_size}...")
            
            documents, metadatas, ids = [], [], []
            
            # Detect travel articles by the presence of `keypoint` list.
            is_travel = bool(batch) and isinstance(batch[0], dict) and "keypoint" in batch[0]
                
            if is_travel:
                import re
                img_re = re.compile(r"\[img\]\s*(.*?)\s*\[img\]", flags=re.IGNORECASE | re.DOTALL)

                for article in batch:
                    try:
                        article_title = str(article.get("title", "") or "").strip()
                        article_time = str(article.get("time", "") or "")
                        url = str(article.get("url", "") or article.get("URL", "") or "").strip()
                        destination = str(article.get("destination", "") or "").strip()

                        for kp in article.get("keypoint", []) or []:
                            idx_info = (kp or {}).get("idx", {}) or {}
                            kp_idx = idx_info.get("idx", 1)
                            kp_title = str(idx_info.get("title", "") or "").strip()
                            kp_context = str(idx_info.get("context", "") or "")

                            if not kp_context.strip():
                                continue

                            images = [m.group(1).strip() for m in img_re.finditer(kp_context) if m.group(1).strip()]
                            cleaned_context = img_re.sub(" ", kp_context).strip()
                            if not cleaned_context.strip():
                                continue

                            doc_content = (
                                f"Title: {article_title} | Spot: {kp_title} | Destination: {destination} | "
                                f"Content: {cleaned_context}"
                            )

                            evaluate = (kp or {}).get("evaluate", {}) or {}
                            try:
                                evaluate_mean = float(evaluate.get("mean", 0.0) or 0.0)
                            except Exception:
                                evaluate_mean = 0.0
                            items = evaluate.get("items", [])
                            evaluate_count = int(len(items)) if isinstance(items, list) else 0

                            # Stable id to avoid duplicates across reruns.
                            id_seed = f"{url}|{article_title}|{kp_idx}|{kp_title}".encode("utf-8", errors="ignore")
                            chunk_id = hashlib.sha1(id_seed).hexdigest()

                            metadata = {
                                "url": url,
                                "article_title": article_title,
                                "keypoint_title": kp_title,
                                "destination": destination,
                                "time": article_time,
                                "keypoint_idx": kp_idx,
                                "evaluate_mean": evaluate_mean,
                                "evaluate_count": evaluate_count,
                                # Keep as JSON string for downstream parsing
                                "images": json.dumps(images, ensure_ascii=False),
                            }

                            documents.append(doc_content)
                            metadatas.append(metadata)
                            ids.append(chunk_id)
                    except Exception as e:
                        print(f"WARNING: Skipping travel article due to processing error: {e}")
            else:
                for recipe in batch:
                    try:
                        recipe_id = f"recipe_{recipe.get('id', recipe.get('URL'))}"
                        content = self._format_recipe_content(recipe)
                        if not content.strip():
                            continue

                        metadata = {
                            "url": recipe.get("URL", ""),
                            "prep_time": recipe.get("Metadata", {}).get("prep_time_minutes", 0),
                            "cook_time": recipe.get("Metadata", {}).get("cook_time_minutes", 0),
                            "servings": recipe.get("Metadata", {}).get("servings", 0),
                        }
                        
                        for nut, details in recipe.get("Nutrition", {}).items():
                            metadata[f"nutr_val_{nut.lower()}"] = details.get("value", 0)
                            metadata[f"nutr_unit_{nut.lower()}"] = details.get("unit", "")
                        
                        documents.append(content)
                        metadatas.append(metadata)
                        ids.append(recipe_id)
                        # Note: count will be updated after successful add
                    except Exception as e:
                        print(f"WARNING: Skipping recipe due to processing error: {e}")

            if not documents:
                continue

            try:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                added = len(ids)
                total_added += added
                print(f"SUCCESS: Added {added} documents to '{collection_name}'.")
            except Exception as e:
                print(f"ERROR: Failed to add batch to ChromaDB: {e}")
        
        print(f"SUCCESS: Finished processing. Total new documents added: {total_added}")
        return total_added

    def add_travel_guides_to_collection(self, collection_name: str, batch_size: int = 100) -> int:
        """TravelChatBot-friendly alias for ingestion."""
        return self.add_recipes_to_collection(collection_name=collection_name, batch_size=batch_size)

    def search(
        self, 
        collection_name: str, 
        query_text: str, 
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Performs semantic search on a ChromaDB collection.
        
        Executes a vector similarity search to find recipes matching the query.
        Supports both semantic text matching and metadata filtering for
        precise recipe discovery.
        
        Args:
            collection_name: Name of the ChromaDB collection to search.
            query_text: Natural language query to search for.
                Examples: "pasta with tomatoes", "low calorie desserts"
            n_results: Maximum number of results to return. Defaults to 5.
            where: Optional metadata filter dictionary for structured filtering.
                Format: {"field": {"$operator": value}}
                Example: {"nutr_val_calories": {"$lte": 500}}
            where_document: Optional document content filter.
                Format: {"$contains": "text_to_find"}
                
        Returns:
            ChromaDB query results containing:
                - documents: List of formatted recipe texts
                - metadatas: List of recipe metadata dicts
                - distances: List of similarity distances
                - ids: List of unique recipe identifiers
                
        Example:
            >>> results = manager.search(
            ...     "recipes", 
            ...     "chicken pasta",
            ...     n_results=10,
            ...     where={"nutr_val_calories": {"$lte": 600}}
            ... )
            >>> print(f"Found {len(results['documents'][0])} recipes")
        """
        collection = self.get_or_create_collection(name=collection_name)
        try:
            query_params = {"query_texts": [query_text], "n_results": n_results}
            if where:
                query_params["where"] = where
            if where_document:
                query_params["where_document"] = where_document
                
            return collection.query(**query_params)
        except Exception as e:
            print(f"ERROR: Failed to query collection '{collection_name}': {e}")
            return []
        
    def prepare_rag_context(
        self, 
        collection_name: str, 
        query_text: str,
        where: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Prepares formatted context for RAG (Retrieval-Augmented Generation).
        
        Searches for relevant recipes and formats them into a context string
        suitable for feeding to an LLM. Handles both semantic search and
        nutrition-based sorting to provide the most relevant information.
        
        Processing pipeline:
            1. Perform vector search with optional metadata filtering
            2. Sort results by nutrition values if requested
            3. Filter by relevance score to ensure quality
            4. Format recipes with metadata and nutrition info
            5. Truncate to fit within token limits
            
        Args:
            collection_name: Name of the ChromaDB collection to search.
            query_text: User's search query in natural language.
            where: Optional metadata filter for structured constraints.
                Example: {"nutr_val_calories": {"$lte": 500}}
            sort_by: Optional nutrition field to sort by.
                Example: "nutr_val_calories" for calorie-based sorting.
            sort_order: Sort direction. "asc" for lowest first,
                "desc" for highest first. Defaults to "asc".
            limit: Maximum number of results when sorting.
                Defaults to 20 for comprehensive context.
                
        Returns:
            Dictionary containing:
                - context: Formatted text ready for LLM consumption
                - sources: List of recipe metadata and URLs for attribution
                - documents_found: Total number of matching recipes found
                
        Example:
            >>> context = manager.prepare_rag_context(
            ...     "recipes",
            ...     "low calorie pasta",
            ...     where={"nutr_val_calories": {"$lte": 400}},
            ...     sort_by="nutr_val_calories",
            ...     sort_order="asc",
            ...     limit=10
            ... )
            >>> print(context["context"])  # Formatted recipes for LLM
        """
        if sort_by:
            n_results = min(max(limit * 3, limit), config.MAX_RESULTS)
        else:
            n_results = limit
        
        results = self.search(
            collection_name=collection_name,
            query_text=query_text,
            where=where,
            n_results=n_results,
            
        )
        
        if not results or not results.get('documents'):
            return {
                "context": "No relevant recipes found.",
                "sources": [],
                "documents_found": 0,
            }
        
        # Sort results if requested
        if sort_by:
            sorted_indices = self._sort_results(results, sort_by, sort_order, limit)
        else:
            sorted_indices = list(range(len(results['documents'][0])))
        
        context_parts, sources = [], []
        max_chars = config.MAX_CONTEXT_TOKENS * 4
        
        for idx in sorted_indices:
            content = results['documents'][0][idx]
            metadata = results['metadatas'][0][idx]
            distance = results['distances'][0][idx]
            # Cosine distance: range [0, 2], convert to similarity [0, 1]
            # distance=0 (identical) -> similarity=1.0
            # distance=2 (opposite) -> similarity=0.0
            similarity = max(0.0, 1.0 - distance)

            # Only return results above the configured cosine-similarity threshold.
            if similarity < config.MIN_RELEVANCE_SCORE:
                continue

            is_travel = 'article_title' in metadata
            
            if is_travel:
                article_title = metadata.get("article_title", "")
                keypoint_title = metadata.get("keypoint_title", "")
                time_str = metadata.get("time", "")
                mean_score = metadata.get("evaluate_mean", 0.0)
                reviews_count = metadata.get("evaluate_count", 0)
                images_str = metadata.get("images", "")
                url = metadata.get("url", "N/A")
                
                cleaned_content = content.split(" | Content: ", 1)[-1] if " | Content: " in content else content
                
                entry_lines = [
                    f"[Relevance: {similarity:.2f}] Title: {article_title} | Spot: {keypoint_title}",
                    f"Content: {cleaned_content}"
                ]
                if images_str:
                    entry_lines.append(f"Images: {images_str}")
                entry_lines.append(f"Published Time: {time_str} | Rating: {mean_score}/5.0 ({reviews_count} reviews) | URL: {url}")
                entry = "\n".join(entry_lines)
            else:
                meta_parts, nutri_parts = [], []
                for key, value in metadata.items():
                    if key.startswith('nutr_val_'):
                        nut_name = key.replace('nutr_val_', '').replace('_', ' ').title()
                        unit = metadata.get(f"nutr_unit_{key.replace('nutr_val_', '')}", '')
                        nutri_parts.append(f"{nut_name}: {value}{unit}")
                    elif key == 'servings':
                        meta_parts.append(f"Servings: {int(value)} people")
                    elif key not in ['url', 'recipe_index'] and not key.startswith('nutr_unit_'):
                        display_key = key.replace('_', ' ').title()
                        meta_parts.append(f"{display_key}: {value}")
                
                metadata_summary = " | ".join(meta_parts)
                if nutri_parts:
                    metadata_summary += " | Nutrition: " + ", ".join(nutri_parts)

                entry = f"[Relevance: {similarity:.2f}] {content}\nMetadata: {metadata_summary}\nURL: {metadata.get('url', 'N/A')}"
            
            if len("\n\n".join(context_parts)) + len(entry) > max_chars:
                break
            
            context_parts.append(entry)
            sources.append({"url": metadata.get('url', ''), "relevance_score": similarity, "metadata": metadata})
        
        if not context_parts:
            return {
                "context": "No sufficiently relevant travel guides found.",
                "sources": [],
                "documents_found": 0,
                "candidates_found": len(results['documents'][0]),
            }

        return {
            "context": "\n\n".join(context_parts),
            "sources": sources,
            "documents_found": len(context_parts),
            "candidates_found": len(results['documents'][0]),
        }

# Module-level instance to act as a singleton
db_manager = ChromaDBManager(
    db_path=str(config.CHROMA_DB_PATH),
    json_path=str(config.PROCESSED_DATA_PATH)
)
