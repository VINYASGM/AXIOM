package eventbus

import (
	"log"
	"time"

	"github.com/nats-io/nats.go"
)

var NATSClient *nats.Conn

func InitNATSClient() (*nats.Conn, error) {
	// Connect to NATS with timeout
	nc, err := nats.Connect("nats://axiom-nats:4222",
		nats.Timeout(5*time.Second),
		nats.MaxReconnects(3),
	)
	if err != nil {
		log.Printf("Warning: Error connecting to nats: %v", err)
		return nil, err
	}

	NATSClient = nc
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
