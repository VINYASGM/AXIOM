package eventbus

import (
	"log"
	"os"
	"time"

	"github.com/nats-io/nats.go"
)

var (
	NATSClient *nats.Conn
	JetStream  nats.JetStreamContext
)

func InitNATSClient() (*nats.Conn, error) {
	// Connect to NATS with timeout
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222" // Default to localhost for local dev
	}
	nc, err := nats.Connect(natsURL,
		nats.Timeout(5*time.Second),
		nats.MaxReconnects(3),
	)
	if err != nil {
		log.Printf("Warning: Error connecting to nats: %v", err)
		return nil, err
	}

	NATSClient = nc

	// Create JetStream Context
	js, err := nc.JetStream()
	if err != nil {
		log.Printf("Warning: Error creating JetStream context: %v", err)
		return nc, err // Return connection even if JS fails, but log it
	}
	JetStream = js

	log.Println("NATS and JetStream initialized successfully")
	return nc, nil
}

func CloseNATSClient() {
	if NATSClient != nil {
		NATSClient.Close()
	}
}

func Publish(subject string, data []byte) error {
	if NATSClient == nil {
		return nats.ErrConnectionClosed
	}
	return NATSClient.Publish(subject, data)
}

func Subscribe(subject string, handler nats.MsgHandler) (*nats.Subscription, error) {
	if NATSClient == nil {
		return nil, nats.ErrConnectionClosed
	}
	return NATSClient.Subscribe(subject, handler)
}
