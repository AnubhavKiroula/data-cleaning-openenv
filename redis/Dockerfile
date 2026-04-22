FROM redis:7-alpine

# Configure Redis with memory limits and LRU eviction
COPY redis.conf /usr/local/etc/redis/redis.conf
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
