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
	"github.com/axiom/api/internal/economics"
	"github.com/axiom/api/internal/eventbus"
	"github.com/axiom/api/internal/handlers"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/orchestration"
	"github.com/axiom/api/internal/speculation"
	"github.com/axiom/api/internal/telemetry"
	"github.com/axiom/api/internal/verifier"
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	"go.uber.org/zap"

	_ "github.com/axiom/api/docs" // Swagger docs
)

// @title AXIOM API
// @version 0.1.0
// @description Core API for AXIOM Autonomous eXecution with Intent-Oriented Modeling.
// @host localhost:8080
// @BasePath /api/v1
// @schemes http
// @securityDefinitions.apikey Bearer
// @in header
// @name Authorization
func main() {
	// Initialize context
	ctx := context.Background()

	// Initialize logger with stdout sync
	zapConfig := zap.NewProductionConfig()
	zapConfig.OutputPaths = []string{"stdout"}
	zapConfig.ErrorOutputPaths = []string{"stderr"}
	logger, err := zapConfig.Build()
	if err != nil {
		log.Fatalf("failed to initialize logger: %v", err)
	}
	defer logger.Sync()

	// Immediate startup log
	logger.Info("AXIOM API starting...",
		zap.String("version", "0.1.0"),
		zap.String("environment", os.Getenv("GO_ENV")),
	)

	logger.Info("Initializing telemetry...")
	// Initialize Telemetry
	shutdownTelemetry, err := telemetry.InitTracer(ctx, "axiom-api")
	if err != nil {
		// Log but don't fail, as collector might be down
		logger.Error("failed to initialize telemetry", zap.Error(err))
	} else {
		defer func() {
			if err := shutdownTelemetry(ctx); err != nil {
				logger.Error("failed to shutdown telemetry", zap.Error(err))
			}
		}()
	}

	logger.Info("Initializing NATS...")
	// Initialize NATS
	_, err = eventbus.InitNATSClient()
	if err != nil {
		logger.Error("failed to connect to NATS", zap.Error(err))
	} else {
		defer eventbus.CloseNATSClient()
		logger.Info("connected to NATS")

		// Initialize JetStream Store
		eventStore, err := eventbus.NewJetStreamStore()
		if err != nil {
			logger.Error("failed to init JetStream store", zap.Error(err))
		} else {
			logger.Info("JetStream Event Store initialized", zap.Any("store", eventStore))
		}
	}

	// Initialize Verifier Client
	logger.Info("Initializing Verifier Client...")
	// In real env: internal.GetEnv("VERIFIER_URL", "localhost:50051")
	verifierClient, err := verifier.NewClient("localhost:50051")
	if err != nil {
		logger.Error("failed to connect to Verifier Service", zap.Error(err))
	} else {
		logger.Info("connected to Verifier Service", zap.Any("client", verifierClient))
	}

	logger.Info("Initializing Temporal...")
	// Initialize Temporal Client
	temporalClient, err := orchestration.InitTemporalClient()
	if err != nil {
		logger.Error("failed to connect to temporal", zap.Error(err))
		// We don't fatal here to allow API to run even if Temporal is down (optional resilience)
	} else {
		defer orchestration.CloseTemporalClient()
		logger.Info("connected to temporal")
	}

	logger.Info("Loading configuration...")
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
	router.Use(middleware.RequestLogger(logger)) // Use new request logger
	router.Use(middleware.CORS())
	router.Use(middleware.RequestID())

	// Swagger documentation
	router.GET("/docs/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// Health check handlers
	healthHandler := handlers.NewHealthHandler(db, rdb, cfg.AIServiceURL)
	router.GET("/health", healthHandler.Health)
	router.GET("/health/deep", healthHandler.DeepHealth)

	// Initialize Economic Service
	economicService := economics.NewService(db, logger)

	logger.Info("Router initialized, setting up handlers...")

	// Initialize handlers
	intentHandler := handlers.NewIntentHandler(db, cfg.AIServiceURL, logger, economicService) // Updated with economics dependency
	generationHandler := handlers.NewGenerationHandler(db, cfg.AIServiceURL, logger, economicService, temporalClient)
	verificationHandler := handlers.NewVerificationHandler(db, cfg.AIServiceURL, verifierClient, logger)
	authHandler := handlers.NewAuthHandler(db, cfg.JWTSecret, logger)
	intelligenceHandler := handlers.NewIntelligenceHandler(db, cfg.AIServiceURL, logger)
	economicsHandler := handlers.NewEconomicsHandler(db, cfg.AIServiceURL, logger, economicService)

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

		// SDE Graph (public for verification)
		v1.GET("/graph", intentHandler.GetGraph)

		// Protected routes with default rate limiting
		protected := v1.Group("")
		protected.Use(middleware.Auth(cfg.JWTSecret))
		protected.Use(middleware.RateLimitMiddleware(middleware.DefaultRateLimiter)) // 100 req/min
		{
			// Cost routes
			cost := protected.Group("/cost")
			{
				cost.POST("/estimate", economicsHandler.EstimateCost)
				cost.GET("/session/:sessionId", economicsHandler.GetSessionCost)
			}

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

			// Generation routes - stricter rate limit + circuit breaker
			generation := protected.Group("/generation")
			generation.Use(middleware.RateLimitMiddleware(middleware.StrictRateLimiter)) // 20 req/min
			generation.Use(middleware.CircuitBreakerMiddleware(middleware.AIServiceCircuitBreaker))
			{
				generation.POST("/start", generationHandler.StartGeneration)
				generation.GET("/:id/status", generationHandler.GetGenerationStatus)
				generation.POST("/:id/cancel", generationHandler.CancelGeneration)
			}

			// Public Verification Routes (Moved for Integration Testing)
			verification := v1.Group("/verification")
			// Note: Circuit breaker skipped for now or needs manual middleware attach if critical
			verification.POST("/verify", verificationHandler.Verify)
			verification.GET("/:id", verificationHandler.GetResult)

			// Protected routes with default rate limiting
			protected := v1.Group("")

			// Project Team routes (Phase 4)
			teamHandler := handlers.NewTeamHandler(db, logger)
			rbac := middleware.NewRBACMiddleware(db, logger)

			project := protected.Group("/project/:projectId")
			// Apply RBAC to project routes
			// For reading list, viewer is enough
			project.GET("/team", rbac.RequirePermission(middleware.PermReadProject), teamHandler.ListMembers)
			// For adding members, need admin (or at least editor? usually admin)
			project.POST("/team/invite", rbac.RequirePermission(middleware.PermManageTeam), teamHandler.AddMember)
			project.DELETE("/team/:userId", rbac.RequirePermission(middleware.PermManageTeam), teamHandler.RemoveMember)

			// User routes
			user := protected.Group("/user")
			{
				user.GET("/me", authHandler.GetCurrentUser)
				user.PUT("/me/settings", authHandler.UpdateSettings)
				user.GET("/learner", intelligenceHandler.GetUserLearner) // Phase 3
				user.POST("/learner/event", intelligenceHandler.PostLearningEvent)
			}

			// Reasoning routes (Phase 3)
			protected.GET("/reasoning/:ivcuId", intelligenceHandler.GetReasoningTrace)

			// Speculation routes (Phase 5)
			speculationEngine := speculation.NewEngine(logger)
			speculationHandler := handlers.NewSpeculationHandler(speculationEngine, logger)
			protected.POST("/speculate", speculationHandler.AnalyzeIntent)
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
