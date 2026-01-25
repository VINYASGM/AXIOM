package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/axiom/api/internal/config"
	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/handlers"
	"github.com/axiom/api/internal/middleware"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

func main() {
	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("failed to initialize logger: %v", err)
	}
	defer logger.Sync()

	// Load configuration
	cfg := config.Load()

	// Debug: print the database URL being used
	log.Printf("DEBUG: Connecting to database: %s", cfg.DatabaseURL)
	log.Printf("DEBUG: Redis URL: %s", cfg.RedisURL)

	// Initialize database
	db, err := database.NewPostgres(cfg.DatabaseURL)
	if err != nil {
		logger.Fatal("failed to connect to database", zap.Error(err))
	}
	defer db.Close()

	// Initialize Redis
	rdb, err := database.NewRedis(cfg.RedisURL)
	if err != nil {
		logger.Fatal("failed to connect to redis", zap.Error(err))
	}
	defer rdb.Close()

	// Setup Gin router
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(middleware.Logger(logger))
	router.Use(middleware.CORS())
	router.Use(middleware.RequestID())

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "axiom-api",
			"version": "0.1.0",
		})
	})

	// Initialize handlers
	intentHandler := handlers.NewIntentHandler(db, cfg.AIServiceURL, logger)
	generationHandler := handlers.NewGenerationHandler(db, cfg.AIServiceURL, logger)
	verificationHandler := handlers.NewVerificationHandler(db, logger)
	authHandler := handlers.NewAuthHandler(db, cfg.JWTSecret, logger)

	// API v1 routes
	v1 := router.Group("/api/v1")
	{
		// Auth routes (public)
		auth := v1.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
			auth.POST("/refresh", authHandler.RefreshToken)
		}

		// Protected routes
		protected := v1.Group("")
		protected.Use(middleware.Auth(cfg.JWTSecret))
		{
			// Intent routes
			intent := protected.Group("/intent")
			{
				intent.POST("/parse", intentHandler.ParseIntent)
				intent.POST("/create", intentHandler.CreateIVCU)
				intent.GET("/:id", intentHandler.GetIVCU)
				intent.PUT("/:id", intentHandler.UpdateIVCU)
				intent.DELETE("/:id", intentHandler.DeleteIVCU)
				intent.GET("/project/:projectId", intentHandler.ListProjectIVCUs)
			}

			// Generation routes
			generation := protected.Group("/generation")
			{
				generation.POST("/start", generationHandler.StartGeneration)
				generation.GET("/:id/status", generationHandler.GetGenerationStatus)
				generation.POST("/:id/cancel", generationHandler.CancelGeneration)
			}

			// Verification routes
			verification := protected.Group("/verification")
			{
				verification.POST("/verify", verificationHandler.Verify)
				verification.GET("/:id", verificationHandler.GetResult)
			}

			// User routes
			user := protected.Group("/user")
			{
				user.GET("/me", authHandler.GetCurrentUser)
				user.PUT("/me/settings", authHandler.UpdateSettings)
			}
		}
	}

	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in goroutine
	go func() {
		logger.Info("starting server", zap.String("port", cfg.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("failed to start server", zap.Error(err))
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("server forced to shutdown", zap.Error(err))
	}

	logger.Info("server exited gracefully")
}
