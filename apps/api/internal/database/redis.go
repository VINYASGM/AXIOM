package database

import (
	"context"

	"github.com/redis/go-redis/v9"
)

// Redis wraps the Redis client
type Redis struct {
	client *redis.Client
}

// NewRedis creates a new Redis client
func NewRedis(redisURL string) (*Redis, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}

	client := redis.NewClient(opts)

	// Test connection
	if err := client.Ping(context.Background()).Err(); err != nil {
		return nil, err
	}

	return &Redis{client: client}, nil
}

// Client returns the underlying Redis client
func (r *Redis) Client() *redis.Client {
	return r.client
}

// Ping checks the Redis connection
func (r *Redis) Ping(ctx context.Context) error {
	return r.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (r *Redis) Close() error {
	return r.client.Close()
}
