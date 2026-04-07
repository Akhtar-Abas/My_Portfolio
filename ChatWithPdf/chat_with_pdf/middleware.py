"""
Rate limiting middleware using in-memory IP tracking with cachetools.
Limits requests per IP address.
"""

import time
from django.http import JsonResponse
from django.conf import settings
from cachetools import TTLCache

# In-memory cache for IP rate limiting
# TTL = time-to-live (in seconds) - entries expire after this time
rate_limit_cache = TTLCache(maxsize=10000, ttl=settings.RATE_LIMIT_WINDOW_SECONDS)


class RateLimitMiddleware:
    """
    Middleware to enforce rate limiting based on client IP address.
    Configuration from settings:
    - RATE_LIMIT_ENABLED: Enable/disable rate limiting
    - RATE_LIMIT_REQUESTS: Number of allowed requests
    - RATE_LIMIT_WINDOW_SECONDS: Time window for requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 10)
        self.window_seconds = getattr(settings, 'RATE_LIMIT_WINDOW_SECONDS', 60)

    def __call__(self, request):
        # Only apply rate limiting to API endpoints
        if self.rate_limit_enabled and request.path.startswith('/api/'):
            client_ip = self._get_client_ip(request)
            
            if self._is_rate_limited(client_ip):
                return JsonResponse(
                    {
                        'error': 'Too many requests. Please try again later.',
                        'status': 429
                    },
                    status=429
                )
        
        response = self.get_response(request)
        return response

    def _get_client_ip(self, request):
        """Extract client IP from request, considering proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_rate_limited(self, client_ip):
        """
        Check if client has exceeded rate limit.
        Tracks request count per IP in time window.
        """
        current_time = time.time()
        
        if client_ip in rate_limit_cache:
            request_times = rate_limit_cache[client_ip]
            
            # Remove old requests outside the time window
            request_times = [
                req_time for req_time in request_times
                if current_time - req_time < self.window_seconds
            ]
            
            # Check if limit exceeded
            if len(request_times) >= self.max_requests:
                return True
            
            # Add current request
            request_times.append(current_time)
            rate_limit_cache[client_ip] = request_times
        else:
            # First request from this IP
            rate_limit_cache[client_ip] = [current_time]
        
        return False
