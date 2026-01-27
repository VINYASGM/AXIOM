package orchestration

import (
	"log"

	"go.temporal.io/sdk/client"
)

var TemporalClient client.Client

func InitTemporalClient() (client.Client, error) {
	// The client is a heavyweight object that should be created once per process.
	c, err := client.Dial(client.Options{
		HostPort: "axiom-temporal:7233",
	})
	if err != nil {
		// Don't use log.Fatalln here - it crashes the server!
		// Return error to allow graceful degradation
		log.Printf("Warning: Unable to create Temporal client: %v", err)
		return nil, err
	}

	TemporalClient = c
	return c, nil
}

func CloseTemporalClient() {
	if TemporalClient != nil {
		TemporalClient.Close()
	}
}
