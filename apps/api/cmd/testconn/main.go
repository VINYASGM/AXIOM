package main

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	url := "postgres://axiom:axiom_dev_password@localhost:5433/axiom?sslmode=disable"
	fmt.Println("Connecting to:", url)

	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		fmt.Printf("Error creating pool: %v\n", err)
		return
	}
	defer pool.Close()

	err = pool.Ping(ctx)
	if err != nil {
		fmt.Printf("Error pinging: %v\n", err)
		return
	}

	fmt.Println("Connection successful!")

	var result int
	err = pool.QueryRow(ctx, "SELECT 1").Scan(&result)
	if err != nil {
		fmt.Printf("Error querying: %v\n", err)
		return
	}

	fmt.Printf("Query result: %d\n", result)
}
