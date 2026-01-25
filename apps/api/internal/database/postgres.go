package database

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Postgres wraps the PostgreSQL connection pool
type Postgres struct {
	pool *pgxpool.Pool
}

// NewPostgres creates a new PostgreSQL connection pool
func NewPostgres(databaseURL string) (*Postgres, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, err
	}

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}

	return &Postgres{pool: pool}, nil
}

// Pool returns the underlying connection pool
func (p *Postgres) Pool() *pgxpool.Pool {
	return p.pool
}

// Close closes the database connection pool
func (p *Postgres) Close() {
	p.pool.Close()
}
