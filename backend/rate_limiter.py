"""Granular Per-User Media-Type Specific Rate Limiter for TravelChatBot REST API.

Enforces separate sliding-window thresholds for standard Text, Speech (audio),
and Vision (image) queries to protect GenAI resources.

Author: TravelChatBot Team
Version: 1.1.0
"""
import time
from typing import Dict, List
from fastapi import Depends, HTTPException, status

from backend.models import User
from backend.auth_utils import get_current_user


class UserRateLimiter:
    """Manages independent sliding-window buffers for Text, Speech, and Vision limits."""

    def __init__(
        self,
        text_limit: int = 15,
        speech_limit: int = 5,
        vision_limit: int = 3
    ):
        self.text_limit = text_limit
        self.speech_limit = speech_limit
        self.vision_limit = vision_limit
        
        # Memory stores mapping user_id -> List of epoch timestamps
        self.text_requests: Dict[int, List[float]] = {}
        self.speech_requests: Dict[int, List[float]] = {}
        self.vision_requests: Dict[int, List[float]] = {}

    def check_rate_limit(self, user_id: int, has_audio: bool = False, has_image: bool = False):
        """Enforces sliding-window rate limits independently based on input media flags."""
        now = time.time()
        
        # 1. Enforce Speech Limit if audio is present
        if has_audio:
            timestamps = self.speech_requests.setdefault(user_id, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            self.speech_requests[user_id] = timestamps
            
            if len(timestamps) >= self.speech_limit:
                retry_after = int(60.0 - (now - timestamps[0]))
                retry_after = max(1, retry_after)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Speech rate limit exceeded. You are allowed a maximum of {self.speech_limit} "
                        f"audio requests per minute. Please try again in {retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)}
                )

        # 2. Enforce Vision Limit if an image is present
        if has_image:
            timestamps = self.vision_requests.setdefault(user_id, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            self.vision_requests[user_id] = timestamps
            
            if len(timestamps) >= self.vision_limit:
                retry_after = int(60.0 - (now - timestamps[0]))
                retry_after = max(1, retry_after)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Vision rate limit exceeded. You are allowed a maximum of {self.vision_limit} "
                        f"image requests per minute. Please try again in {retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)}
                )

        # 3. Enforce Standard Text Limit only if NEITHER audio nor image is present
        if not has_audio and not has_image:
            timestamps = self.text_requests.setdefault(user_id, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            self.text_requests[user_id] = timestamps
            
            if len(timestamps) >= self.text_limit:
                retry_after = int(60.0 - (now - timestamps[0]))
                retry_after = max(1, retry_after)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Text rate limit exceeded. You are allowed a maximum of {self.text_limit} "
                        f"text requests per minute. Please try again in {retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)}
                )

        # 4. If all validations passed, record the current request time in corresponding buffers
        if has_audio:
            self.speech_requests[user_id].append(now)
        if has_image:
            self.vision_requests[user_id].append(now)
        if not has_audio and not has_image:
            self.text_requests[user_id].append(now)


# Instantiates global rate limiter with Text=15, Speech=5, Vision=3 limits
chat_rate_limiter = UserRateLimiter(
    text_limit=15,
    speech_limit=5,
    vision_limit=3
)
