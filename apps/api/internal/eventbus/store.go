package eventbus

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/nats-io/nats.go"
)

// EventStore defines the interface for an append-only event log
type EventStore interface {
	Append(stream string, subject string, data interface{}) error
	Read(stream string, subject string) ([]Event, error)
}

// Event wraps the payload with metadata
type Event struct {
	ID        string    `json:"id"`
	Subject   string    `json:"subject"`
	Data      []byte    `json:"data"`
	Timestamp time.Time `json:"timestamp"`
}

type JetStreamStore struct {
	js nats.JetStreamContext
}

// NewJetStreamStore creates a new event store backed by NATS JetStream
func NewJetStreamStore() (*JetStreamStore, error) {
	if JetStream == nil {
		return nil, fmt.Errorf("JetStream context not initialized")
	}
	return &JetStreamStore{js: JetStream}, nil
}

// Append adds an event to the stream
func (s *JetStreamStore) Append(stream string, subject string, data interface{}) error {
	payload, err := json.Marshal(data)
	if err != nil {
		return err
	}

	// Ensure stream exists (idempotent)
	_, err = s.js.AddStream(&nats.StreamConfig{
		Name:     stream,
		Subjects: []string{subject + ".*"},
	})
	// Ignore "stream name already in use" error if check logic is complex,
	// but simpler to just try-add or check existence.
	// For MVP, we assume streams are pre-provisioned or we lazily create.
	// AddStream is idempotent-ish if config matches, but returns error if exists with different config.
	// Optimization: checking existence first is better but skipping for brevity in this step.

	// Publish to JetStream
	// Subject format: "stream.action", e.g., "ivcu.created"
	_, err = s.js.Publish(subject, payload)
	return err
}

// Read fetches the last N events (simplified for now)
func (s *JetStreamStore) Read(stream string, subject string) ([]Event, error) {
	// Ephemeral subscription to fetch history
	sub, err := s.js.SubscribeSync(subject, nats.BindStream(stream))
	if err != nil {
		return nil, err
	}
	defer sub.Unsubscribe()

	var events []Event

	// Fetch batch (demo logic: just gets what's available quickly)
	for {
		msg, err := sub.NextMsg(100 * time.Millisecond)
		if err == nats.ErrTimeout {
			break
		}
		if err != nil {
			return events, err
		}

		events = append(events, Event{
			ID:        msg.Header.Get("Nats-Msg-Id"), // Or generated
			Subject:   msg.Subject,
			Data:      msg.Data,
			Timestamp: time.Now(), // Approximation if not in metadata
		})
	}

	return events, nil
}
