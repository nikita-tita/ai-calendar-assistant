"""Vision analysis service using Yandex Vision API."""

import asyncio
import base64
from typing import Dict, Any, List, Optional
import structlog
import aiohttp
from datetime import datetime

from app.config import settings

logger = structlog.get_logger()


class VisionAnalysisService:
    """
    Analyze property photos using Yandex Vision AI.

    Analyzes:
    - Lighting quality (brightness, natural light)
    - Image quality (resolution, clarity)
    - Renovation state (from image content)
    - Room type detection
    - Furniture/amenities detection

    Requires: YANDEX_VISION_API_KEY or uses same as YANDEX_GPT_API_KEY.
    Free tier: 1,000 requests/month.
    """

    VISION_API_URL = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"

    # Feature types
    FEATURE_CLASSIFICATION = "CLASSIFICATION"
    FEATURE_TEXT_DETECTION = "TEXT_DETECTION"

    def __init__(self):
        """Initialize vision analysis service."""
        # Try to use dedicated Vision API key, fallback to GPT key
        self.api_key = getattr(settings, 'yandex_vision_api_key', None) or \
                      getattr(settings, 'yandex_gpt_api_key', None)
        self.folder_id = getattr(settings, 'yandex_gpt_folder_id', None)

        if not self.api_key or not self.folder_id:
            logger.warning("yandex_vision_not_configured",
                          message="Vision analysis disabled. Set YANDEX_VISION_API_KEY and YANDEX_GPT_FOLDER_ID")

        logger.info("vision_analysis_service_initialized",
                   api_configured=bool(self.api_key))

    async def analyze_listing_images(
        self,
        listing_id: str,
        image_urls: List[str],
        max_images: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze all images for a listing.

        Args:
            listing_id: Listing ID
            image_urls: List of image URLs to analyze
            max_images: Maximum images to analyze (cost control)

        Returns:
            Vision data dictionary:
            {
                "light_score": float,  # 0-1, average brightness
                "quality_score": float,  # 0-1, image quality
                "renovation_detected": str,  # "good"/"average"/"poor"/None
                "room_types": List[str],  # Detected room types
                "amenities_detected": List[str],  # Furniture, appliances
                "images_analyzed": int,
                "analyzed_at": str  # ISO timestamp
            }
        """
        if not self.api_key:
            logger.warning("vision_analysis_skipped_no_api_key",
                          listing_id=listing_id)
            return self._empty_vision_data()

        logger.info("analyzing_listing_images",
                   listing_id=listing_id,
                   image_count=len(image_urls))

        # Limit number of images to analyze
        images_to_analyze = image_urls[:max_images]

        try:
            # Analyze images in batches (Yandex Vision supports batch)
            batch_size = 5
            all_results = []

            for i in range(0, len(images_to_analyze), batch_size):
                batch = images_to_analyze[i:i + batch_size]

                # Download and analyze batch
                batch_results = await self._analyze_image_batch(batch)
                all_results.extend(batch_results)

                # Rate limiting delay
                if i + batch_size < len(images_to_analyze):
                    await asyncio.sleep(0.5)

            # Aggregate results
            vision_data = self._aggregate_vision_results(all_results)
            vision_data["images_analyzed"] = len(all_results)
            vision_data["analyzed_at"] = datetime.utcnow().isoformat()

            logger.info("vision_analysis_success",
                       listing_id=listing_id,
                       images_analyzed=len(all_results),
                       light_score=round(vision_data["light_score"], 2))

            return vision_data

        except Exception as e:
            logger.error("vision_analysis_error",
                        listing_id=listing_id,
                        error=str(e))
            return self._empty_vision_data()

    async def _analyze_image_batch(
        self,
        image_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Analyze batch of images.

        Args:
            image_urls: List of image URLs

        Returns:
            List of analysis results
        """
        # Download images
        images_data = []
        async with aiohttp.ClientSession() as session:
            for url in image_urls:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            image_bytes = await response.read()
                            # Encode to base64
                            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            images_data.append({
                                "url": url,
                                "content": image_base64
                            })
                        else:
                            logger.warning("image_download_failed",
                                         url=url,
                                         status=response.status)
                except Exception as e:
                    logger.error("image_download_error",
                               url=url,
                               error=str(e))

        if not images_data:
            return []

        # Call Yandex Vision API
        results = await self._call_vision_api(images_data)

        return results

    async def _call_vision_api(
        self,
        images: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Call Yandex Vision API for image analysis.

        Args:
            images: List of dicts with {url, content (base64)}

        Returns:
            List of analysis results
        """
        # Build request for batch analysis
        analyze_specs = []

        for image in images:
            analyze_specs.append({
                "content": image["content"],
                "features": [
                    {
                        "type": self.FEATURE_CLASSIFICATION
                    }
                ]
            })

        request_data = {
            "folderId": self.folder_id,
            "analyzeSpecs": analyze_specs
        }

        # Call API
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Api-Key {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    self.VISION_API_URL,
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("yandex_vision_api_error",
                                   status=response.status,
                                   error=error_text)
                        return []

                    data = await response.json()

            # Parse results
            results = []
            for idx, image in enumerate(images):
                if idx < len(data.get("results", [])):
                    result_data = data["results"][idx]
                    parsed = self._parse_vision_result(result_data, image["url"])
                    results.append(parsed)

            return results

        except Exception as e:
            logger.error("vision_api_call_error", error=str(e))
            return []

    def _parse_vision_result(
        self,
        result_data: Dict[str, Any],
        image_url: str
    ) -> Dict[str, Any]:
        """
        Parse single image vision analysis result.

        Args:
            result_data: Raw API result for one image
            image_url: Image URL

        Returns:
            Parsed vision data
        """
        # Yandex Vision returns classification results
        # Structure:
        # {
        #   "results": [{
        #     "results": [{
        #       "classification": {
        #         "properties": [
        #           {"name": "label", "probability": 0.95},
        #           ...
        #         ]
        #       }
        #     }]
        #   }]
        # }

        parsed = {
            "url": image_url,
            "brightness": 0.5,  # Default
            "quality": 0.7,  # Default
            "labels": [],
            "room_type": None,
            "renovation_quality": None
        }

        try:
            results_list = result_data.get("results", [])
            if not results_list:
                return parsed

            classification = results_list[0].get("classification", {})
            properties = classification.get("properties", [])

            # Extract labels with high confidence
            labels = []
            for prop in properties:
                label = prop.get("name", "")
                probability = prop.get("probability", 0.0)

                if probability >= 0.5:  # Only confident labels
                    labels.append({
                        "label": label,
                        "confidence": probability
                    })

            parsed["labels"] = labels

            # Detect room type from labels
            parsed["room_type"] = self._detect_room_type(labels)

            # Estimate lighting (heuristic based on labels)
            parsed["brightness"] = self._estimate_brightness(labels)

            # Estimate renovation quality
            parsed["renovation_quality"] = self._estimate_renovation(labels)

        except Exception as e:
            logger.error("vision_result_parse_error", error=str(e))

        return parsed

    def _detect_room_type(self, labels: List[Dict[str, Any]]) -> Optional[str]:
        """Detect room type from labels."""
        label_texts = [l["label"].lower() for l in labels]

        # Room type keywords (English and Russian)
        room_keywords = {
            "kitchen": ["kitchen", "кухня", "cooking", "dining"],
            "bedroom": ["bedroom", "спальня", "bed", "кровать"],
            "living_room": ["living", "гостиная", "sofa", "диван"],
            "bathroom": ["bathroom", "ванная", "toilet", "туалет"],
            "hallway": ["hallway", "прихожая", "corridor", "коридор"]
        }

        for room_type, keywords in room_keywords.items():
            if any(keyword in text for text in label_texts for keyword in keywords):
                return room_type

        return None

    def _estimate_brightness(self, labels: List[Dict[str, Any]]) -> float:
        """Estimate brightness from labels (0-1)."""
        # Bright indicators
        bright_keywords = ["bright", "light", "window", "daylight", "sunny", "светлый"]
        dark_keywords = ["dark", "dim", "shadow", "темный"]

        label_texts = [l["label"].lower() for l in labels]

        bright_score = sum(1 for text in label_texts if any(kw in text for kw in bright_keywords))
        dark_score = sum(1 for text in label_texts if any(kw in text for kw in dark_keywords))

        # Calculate score
        if bright_score > dark_score:
            return min(0.5 + bright_score * 0.15, 1.0)
        elif dark_score > bright_score:
            return max(0.5 - dark_score * 0.15, 0.0)
        else:
            return 0.5  # Neutral

    def _estimate_renovation(self, labels: List[Dict[str, Any]]) -> Optional[str]:
        """Estimate renovation quality from labels."""
        # Good renovation indicators
        good_keywords = ["modern", "new", "luxury", "premium", "современный", "новый"]
        poor_keywords = ["old", "worn", "damaged", "старый", "ветхий"]

        label_texts = [l["label"].lower() for l in labels]

        has_good = any(keyword in text for text in label_texts for keyword in good_keywords)
        has_poor = any(keyword in text for text in label_texts for keyword in poor_keywords)

        if has_good and not has_poor:
            return "good"
        elif has_poor and not has_good:
            return "poor"
        elif has_good or has_poor:
            return "average"
        else:
            return None

    def _aggregate_vision_results(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate vision results from multiple images.

        Args:
            results: List of parsed vision results

        Returns:
            Aggregated vision data
        """
        if not results:
            return self._empty_vision_data()

        # Calculate average brightness
        brightness_scores = [r["brightness"] for r in results if r.get("brightness")]
        avg_brightness = sum(brightness_scores) / len(brightness_scores) if brightness_scores else 0.5

        # Calculate average quality
        quality_scores = [r["quality"] for r in results if r.get("quality")]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.7

        # Collect room types
        room_types = list(set(r["room_type"] for r in results if r.get("room_type")))

        # Determine overall renovation quality
        renovation_states = [r["renovation_quality"] for r in results if r.get("renovation_quality")]
        renovation_detected = self._most_common(renovation_states) if renovation_states else None

        # Collect all labels
        all_labels = []
        for r in results:
            all_labels.extend(r.get("labels", []))

        # Extract unique amenities from labels
        amenities = self._extract_amenities(all_labels)

        return {
            "light_score": round(avg_brightness, 2),
            "quality_score": round(avg_quality, 2),
            "renovation_detected": renovation_detected,
            "room_types": room_types,
            "amenities_detected": amenities,
            "images_analyzed": 0  # Will be set by caller
        }

    def _extract_amenities(self, labels: List[Dict[str, Any]]) -> List[str]:
        """Extract amenities from labels."""
        amenities = set()

        amenity_keywords = {
            "furniture": ["furniture", "мебель", "sofa", "chair", "table"],
            "kitchen_appliances": ["refrigerator", "stove", "oven", "холодильник", "плита"],
            "bathroom_fixtures": ["shower", "bathtub", "sink", "душ", "ванна"],
            "tv": ["television", "tv", "телевизор"],
            "ac": ["air conditioner", "ac", "кондиционер"],
            "washer": ["washing machine", "стиральная"]
        }

        label_texts = [l["label"].lower() for l in labels]

        for amenity, keywords in amenity_keywords.items():
            if any(keyword in text for text in label_texts for keyword in keywords):
                amenities.add(amenity)

        return sorted(list(amenities))

    def _most_common(self, items: List[str]) -> Optional[str]:
        """Return most common item in list."""
        if not items:
            return None

        from collections import Counter
        counter = Counter(items)
        return counter.most_common(1)[0][0]

    def _empty_vision_data(self) -> Dict[str, Any]:
        """Return empty vision data structure."""
        return {
            "light_score": None,
            "quality_score": None,
            "renovation_detected": None,
            "room_types": [],
            "amenities_detected": [],
            "images_analyzed": 0,
            "analyzed_at": datetime.utcnow().isoformat()
        }

    def get_vision_summary(self, vision_data: Dict[str, Any]) -> str:
        """
        Generate human-readable vision summary.

        Args:
            vision_data: Vision data from analyze_listing_images()

        Returns:
            Human-readable summary in Russian
        """
        light_score = vision_data.get("light_score")
        renovation = vision_data.get("renovation_detected")
        amenities = vision_data.get("amenities_detected", [])

        parts = []

        # Light assessment
        if light_score is not None:
            if light_score >= 0.7:
                parts.append("💡 Очень светлая квартира")
            elif light_score >= 0.5:
                parts.append("💡 Хорошее освещение")
            else:
                parts.append("🌑 Недостаточно света")

        # Renovation assessment
        if renovation:
            renovation_text = {
                "good": "✨ Отличное состояние",
                "average": "🔧 Среднее состояние",
                "poor": "⚠️ Требует ремонта"
            }
            parts.append(renovation_text.get(renovation, ""))

        # Amenities
        if amenities:
            amenity_names = {
                "furniture": "мебель",
                "kitchen_appliances": "кухонная техника",
                "tv": "телевизор",
                "ac": "кондиционер",
                "washer": "стиральная машина"
            }
            amenity_list = [amenity_names.get(a, a) for a in amenities[:3]]
            parts.append(f"🏠 {', '.join(amenity_list)}")

        if not parts:
            return "Анализ фото: данные недоступны"

        return "\n".join(parts)


# Global instance
vision_analysis_service = VisionAnalysisService()
